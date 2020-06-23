
#needed modules
import pandas as pd
import numpy as np
import re
import requests
import wordninja
import nltk
import string
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
    job_titles = pd.read_csv('titles.txt', header=None)[0].values.tolist()
    
    def __init__(self):
        self.today = datetime.now().strftime('%a, %B %d, %Y')
        self.daily = '1'
        self.weekly = '1%2C2'
        self.links = self.get_all_location_results()
        self.postings = []
        
    def process_retrieved_postings(self):
        for link in self.links:
            post = Posting(link=link)
            if post: self.postings.append(post)
        self.postings = list(filter(self.filter_title_and_location, self.postings))
        
    def save_processed_postings(self):
        data = self.get_job_postings()
        data.sort_values(by='decision', ascending = False)
        data.to_excel('Job Postings -' + self.today)
        print('File exported!')
        
    #method to get search results for dictionary positions and all locations before filtering
    #Posted in the last 24 hours and <= 10 miles from job location
    def get_all_location_results(self, location = 'United States'): 
        end = len(self.job_titles)
        self.links = []
        print(end, 'search terms: \n--------------------------------\n')
        period = self.daily
        if self.today[0:3] == 'Sun': period = self.weekly
        for title in self.job_titles:
            URL = 'https://www.linkedin.com/jobs/search?keywords='+ title + '&location='\
            + location + '&f_TP=' + period 
            page = requests.get(URL)
            soup = bs(page.content, 'lxml')
            refs = soup.find_all('a', class_='result-card__full-card-link')
            self.links += [ref.get('href') for ref in refs if ref.get('href') not in self.links]
        print(location + ':', len(self.links), 'result links for', self.today)
        return self.links
    
    #method to check whether title is valid for entry, associate, internship level, non-government job
    def filter_title_and_location(self, job, filters): #true is the thing we want to keep
        filters = ['VP', 'manager', 'senior', 'sr', 'president', 'vice president', 'director']
        #check if title has senior tags/location is Virginia = government jobs/need clearance+residence
        try:
            for w in filters:
                if job.job_title.upper().find(w.upper()) != -1: return False
            if job.job_location.upper().find(', VA') != -1: return False
            else: return True
        except: pass
        
    #method to return the processed job postings as a dataframe
    def get_job_postings(self):
        #filter out non-qualified jobs
        print('Total remaining job postings:', len(self.postings))
        companies = jdf.get_H1B_approvers()
        jobs = []
        for p in self.postings:
            val = jdf.Description_Features(p.description)
            jobs.append({'title': p.job_title, 'company': p.company_name, 
                         'location': p.job_location, 'desc_raw': p.description,
                        'desc_visa': val.clean_description_text(),
                        'sponsor':val.get_immigration_stance(p.company_name, companies),
                        'decision': val.check_description_markers(5)}) #might change letter
        self.job_data = pd.DataFrame(jobs)
        return self.job_data
    
    
    
    
#class to preprocess the description and get target description for feature extraction
class Description_Features:    
    #tags to filter description with for immigration
    immigration_tags = ['security', 'clearance', 'citizens', 'citizen', 'H1B', 'U.S.','C2C', 'W2',
                             'authorized', 'authorization', 'sponsorship', 'visa',  'citizen',  
                             'eligible',  'TSSCI',  'DoD', 'secret', 'resident', 'W2', 'persons',
                             'equal', 'employment', 'EEO', 'citizenship', 'immigration', 'status']
    
    def __init__(self, text = None):
        if text: self.description = text
        self.wn = WordNetLemmatizer()
        self.immigration_tags = [tag.lower() for tag in self.immigration_tags]
        self.health = ['health', 'mental', 'pharma', 'medicine', 'prescription', 'drugs']
        self.yes = ['citizenship', 'status','EEO','equal', 'employment', 'regardless', 'available',
                    'national', 'origin', 'does', 'not', 'discriminate', 'EEOC']
        self.no = ['must', 'required', 'clearance', 'citizen','resident', 'not', 'permanent', 'US',
                   'EAD', 'green', 'card', 'work', 'authorization', 'authorized', 'U.S.', 'H1B'
                   'unable', 'sponsorship', 'DoD', 'active', 'offer', 'does','only', 'citizenship']
    
    #allows you to parse through text to see if some words are attached by mistake and add a space
    def parsing_description(self):
        desc = []
        for word in self.description.split(' '):
            if len(word) <= 8: desc.append(word)
            else: desc.append(' '.join(wordninja.split(word)))
        self.description = ' '.join(desc)
        return self.description
    
    def filter_tags(self, desc):
        check = 0
        for tag in self.immigration_tags:
            if desc.lower().find(tag) != -1: check += 1 #tag found
        if check <= 1: return False
        else: return True

    def target_description(self):
        #get sentence tokens from semi-cleaned description and filter out ones with no target tags
        self.description = re.sub(r'\.(?! )', '. ', self.description)
        sents = sent_tokenize(self.description)
        sents = list(filter(self.filter_tags, sents))
        if len(sents) == 0: sents.append('check company stance')
        self.filtered_desc = ' '.join(sents)
        return self.filtered_desc
    
    #ML pipeline to parse description, tokenize, lower case, get target lemmatized tokens (joined)
    def clean_description_text(self):
        #cleaning a description
        #remove/ignore non-ASCII characters and years
        self.description = re.sub(r'[^\x00-\x7f]', '', self.description) 
        self.description = re.sub(r'[0-9]{3,}', '', self.description)
        #make sure all words are displayed correctly/no words attached by mistake, remove stopwords
        desc = self.parsing_description()
        no_stopwords = ['for', 'no', 'not', 'only', 'does', 'be', 'doesn\'t']
        stops = [w for w in stopwords.words('english') if w not in no_stopwords]
        self.description = ' '.join([w.lower() for w in desc.split() if w.lower() not in stops])
        self.description = desc.lower()
        
        #only get sentences with immigration indicator words/phrases (requires sent_tokenization)
        desc = self.target_description()
        #remove unwanted/non-context punctuation marks after un-tokenizing sentences
        filters = ''.join([x for x in string.punctuation if x != '#' and x != '+'])
        desc = ''.join([char for char in desc if char not in filters])
        self.filtered_desc = ''
        for word in word_tokenize(desc.lower()):
            if len(word) > 3: self.filtered_desc += self.wn.lemmatize(word) + ' '
            else: self.filtered_desc += word + ' '
        return self.filtered_desc
    
    #method to check immigration stance based on description or company (from H1B list)
    def get_immigration_stance(self, comp, companies_list):
        self.immigration = 'Unknown'
        if 'check company stance' in self.filtered_desc:  
            for org in companies_list:
                flag = [] #tracking companies names from H1B list
                if comp.lower() in org.lower() or comp.lower() in org.lower(): flag.append(True)
                if True in flag: self.immigration = 'Yes'
        return self.immigration                    
    
    def collocation_finder(self, n_gram_total, n_gram_filter_word):
        cf = TrigramCollocationFinder.from_words(word_tokenize(self.filtered_desc)) 
        #checking what words appear frequently with 'word' in this case it is 'work'
        n_filter = lambda *words: n_gram_filter_word not in words
        cf.apply_ngram_filter(n_filter)
        #apply frq filter removes occurences that happened less than x times
        self.collocation_scores = cf.nbest(TrigramAssocMeasures.likelihood_ratio, n_gram_total)
        return self.collocation_scores
    
    def get_decision_trigrams(self, n_grams):
        #get trigrams for target words and phrases
        self.yes_trigrams, self.no_trigrams = [], []
        yes_grams, no_grams = [], []
        for word in self.yes:
            yes_grams += self.collocation_finder(n_grams, word.lower())
        for word in self.no:
            no_grams += self.collocation_finder(n_grams, word.lower())
        for tup in yes_grams: self.yes_trigrams.append(' '.join([x for x in tup]))
        for tup in no_grams: self.no_trigrams.append(' '.join([x for x in tup]))
        return self.yes_trigrams, self.no_trigrams
    
    def check_description_markers(self, n_grams): 
        #check if trigrams for target words and phrases are satisfactory to set target feature
        target_grams = self.get_decision_trigrams(n_grams)
        grams_ct = [len(target_grams[0])/len(self.yes), len(target_grams[1])/len(self.no)]
        if grams_ct[1] > grams_ct[0]: #we might change desired number later
            self.target = 'N'
        elif grams_ct[0] > grams_ct[1] or self.immigration == 'Yes':
            self.target = 'Y'
        else: self.target = 'Unk'
        return self.target  
    
    
    
    
#method to get the company names for top H1B approved companies for the current year
def get_H1B_approvers(pages = range(1,5)):
    h1b_companies = []
    for page in pages:
        URL = 'http://www.myvisajobs.com/Reports/2020-H1B-Visa-Sponsor.aspx?P=' + str(page)
        page = requests.get(URL)
        soup = bs(page.content, 'lxml')
        table = soup.find('table', class_='tbl').find_all('tr')[1:] #minus header row
        for tr in table: 
            try: h1b_companies.append(tr.find_all('td')[1].text)
            except: pass
    return h1b_companies

#time printer
def print_time(note, t):
    print(note, '{m}:{s:02d} mins'\
          .format(m = round((time() - t )/ 60), s = round((time()-t)%60)))
