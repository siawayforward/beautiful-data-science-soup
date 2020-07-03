#needed modules
import pandas as pd
import numpy as np
import re
import requests
import wordninja
import nltk
import string
import job_description
from bs4 import BeautifulSoup as bs
from collections import defaultdict
from datetime import datetime, timedelta
from nltk.corpus import stopwords
from time import time
from nltk import WordNetLemmatizer
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.collocations import TrigramCollocationFinder
from nltk.metrics import TrigramAssocMeasures

#class for each job posting
class Posting:        
    def __init__(self, link):
        self.job_link = link
        #get details and assign to attributes
        try:
            details = self.get_job_posting_info()
            if details:
                self.job_title = details.get('title')
                self.company_name = details.get('company')
                self.job_location = details.get('location')
                self.description = details.get('desc')
            else: self = None
        except: pass

    #method to get the info in the links in order
    def get_job_posting_info(self):      
        #get page data
        page = requests.get(self.job_link)
        soup = bs(page.content, 'lxml')
        #get value fields
        job = soup.find('h1', 'topcard__title')
        location = soup.find('span', 'topcard__flavor topcard__flavor--bullet')
        company = soup.find('a', 'topcard__org-name-link topcard__flavor--black-link')
        desc = soup.find('div', 'description__text description__text--rich')
        if job is not None and location is not None and company is not None and desc is not None:
            #add job attributes if verified
            job = job.get_text().strip()
            location = location.get_text().strip()
            company = company.get_text().strip()
            desc = desc.get_text()
            details = {'title': job, 'location': location, 'company': company, 'desc': desc}
            return details
        else: return None
            
            
            
            
#class to find, filter, and process job postings
class New_Postings:
    #jobs to search
    job_titles = pd.read_csv('job-titles.txt', header=None)[0].values.tolist()
    
    def __init__(self):
        self.date = datetime.now()
        self.daily = '1'
        self.weekly = '1%2C2'
        self.links = self.get_all_location_results()
        self.postings = []
        
    def process_retrieved_postings(self):
        for link in self.links:
            post = Posting(link=link)
            if post: self.postings.append(post)
        self.postings = list(filter(self.filter_title_and_location, self.postings))
        
    def save_job_postings(self):
        data = self.get_job_postings()
        del data['desc_visa'] #remove processed description
        data.sort_values(by=['decision'], inplace=True, ascending=False)
        data = data.reset_index(drop=True)
        data.to_excel('Job Postings -' + self.date.strftime('%Y-%m-%d')+'.xlsx')
        print('File exported!')
        
    #method to get search results for dictionary positions and all locations before filtering
    #Posted in the last 24 hours and <= 10 miles from job location
    def get_all_location_results(self, location = 'United States'): 
        end = len(self.job_titles)
        self.links = []
        print(end, 'search terms: \n--------------------------------')
        period = self.daily
        if self.date.strftime('%a') == 'Sun': period = self.weekly
        for title in self.job_titles:
            URL = 'https://www.linkedin.com/jobs/search?keywords='+ title + '&location='\
            + location + '&f_TP=' + period 
            page = requests.get(URL)
            soup = bs(page.content, 'lxml')
            refs = soup.find_all('a', class_='result-card__full-card-link')
            self.links += [ref.get('href') for ref in refs if ref.get('href') not in self.links]
        print(location + ':', len(self.links), 'result links for', self.date.strftime('%a %B %d, %Y'))
        return self.links
    
    #method to check whether title is valid for entry, associate, internship level, non-government job
    def filter_title_and_location(self, job): #true is the thing we want to keep
        filters = ['VP', 'manager', 'senior', 'sr', 'president', 'vice president', 'director']
        #check if title has senior tags/location is Virginia = government jobs/need clearance+residence
        try:
            for w in filters:
                if job.job_title.upper().find(w.upper()) != -1: return False
            if job.job_location.upper().find(', VA') != -1: return False
            else: return True
        except: pass

    #to use later - method to get immigration decision
    #method to return the processed job postings as a dataframe
    def get_job_postings(self):
        #filter out non-qualified jobs
        print('Total remaining job postings:', len(self.postings))
        companies = job_description.get_H1B_approvers()
        jobs = []
        for p in self.postings:
            val = job_description.Description_Features(p.description)
            jobs.append({'title': p.job_title, 'company': p.company_name, 
                            'location': p.job_location, 'desc_raw': p.description,
                        'desc_visa': val.clean_description_text(),
                        'sponsor':val.get_immigration_stance(p.company_name, companies),
                        'decision': val.check_description_markers(5)}) #might change letter
        job_data = pd.DataFrame(jobs)
        return job_data
  
    


#time printer
def print_time(note, t):
    print(note, '{m}:{s:02d} mins'\
          .format(m = round((time() - t )/ 60), s = round((time()-t)%60)))
