import pandas as pd
import numpy as np
import re
import requests
import wordninja
import string
from time import time
from bs4 import BeautifulSoup as bs
from nltk import WordNetLemmatizer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.collocations import TrigramCollocationFinder, TrigramAssocMeasures

#class to preprocess the description and get target description for feature extraction
class Description_Features:    
    #tags to filter description with for immigration
    immigration_tags = ['security', 'clearance', 'citizens', 'citizen', 'H1B', 'U.S.','C2C', 'W2',
                             'authorized', 'authorization', 'sponsorship', 'visa',  'citizen', 'e-verify'
                             'eligible',  'TSSCI',  'DoD', 'secret', 'resident', 'W2', 'persons',
                             'equal', 'employment', 'EEO', 'citizenship', 'immigration', 'status']
    
    def __init__(self, text = None):
        if text: self.description = text
        self.wn = WordNetLemmatizer()
        self.immigration_tags = [tag.lower() for tag in self.immigration_tags]
        self.health = ['health', 'mental', 'pharma', 'medicine', 'prescription', 'drugs']
        self.yes = ['citizenship', 'status','EEO','equal', 'employment', 'regardless', 'available',
                    'national', 'origin', 'does', 'not', 'discriminate', 'EEOC', 'e-verify']
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
        filters = ''.join([x for x in string.punctuation if x != '#' and x != '+' and x != '-'])
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