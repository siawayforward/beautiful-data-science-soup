
#modules needed
import nltk
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup as bs
import string
from nltk.corpus import stopwords
from nltk import WordNetLemmatizer
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.collocations import TrigramCollocationFinder
from nltk.metrics import TrigramAssocMeasures
import wordninja

#class to preprocess the description and get target description for feature extraction
class Description_Features():    
    #tags to filter description with for immigration
    immigration_tags = ['security clearance', 'citizens', 'citizen', 'green card', 
                             'authorized', 'authorization', 'sponsorship', 'visa', 'US citizen',  
                             'eligible',  'TS/SCI',  'DoD', 'secret clearance', 'resident', 'W2'
                             'US persons', 'equal employment', 'EEO', 'citizenship', 'immigration',
                             'citizenship status', 'No C2C', 'W2 only', 'visas', 'clearance'
                            ]
    wn = WordNetLemmatizer()
    
    def __init__(self, text = None):
        if text: self.description = text
        self.immigration_tags = [tag.lower() for tag in self.immigration_tags]
    
    #allows you to parse through text to see if some words are attached by mistake and add a space
    def parsing_description(self):
        desc = []
        for word in self.description.split():
            if len(word) <= 8: desc.append(word)
            else: desc.append(' '.join(wordninja.split(word)))
        self.description = ' '.join(desc)
        return self.description
    
    def filter_tags(self, desc):
        check = 0
        for tag in self.immigration_tags:
            if desc.lower().find(tag) != -1: check += 1 #tag found
        if check == 0: return False
        else: return True

    def target_description(self):
        #get sentence tokens from semi-cleaned description and filter out ones with no target tags
        sents = sent_tokenize(self.description)
        sents = list(filter(self.filter_tags, sents))
        if len(sents) == 0: sents.append('check company stance')
        self.filtered_description = ' '.join(sents)
        return self.filtered_description
    
    #ML pipeline to parse description, tokenize, lower case, get target lemmatized tokens (joined)
    def clean_description_text(self):
        #cleaning a description
        #remove/ignore non-ASCII characters
        self.description = re.sub(r'[^\x00-\x7f]', '', self.description) 
        #make sure all words are displayed correctly/no words attached by mistake, remove stopwords
        desc = self.parsing_description()
        stops = [stop for stop in stopwords.words('english') if stop not in ['no', 'not', 'only']]
        self.description = ' '.join([w.lower() for w in desc.split() if w.lower() not in stops])

        #only get sentences with immigration indicator words/phrases (requires sent_tokenization)
        filter_desc = self.target_description()
        #remove unwanted/non-context punctuation marks after un-tokenizing sentences
        filters = ''.join([x for x in string.punctuation if x != '#' and x != '+'])
        desc = ''.join([char for char in filter_desc if char not in filters])
        self.filtered_description = ' '.join([wn.lemmatize(word) for word in word_tokenize(desc)])
        return self.filtered_description
    
    #lemmatize the descriptions and create tokens
    def tokenize(self):
        if self.filtered_description == 'check company stance': self.tokens = ''
        else: self.tokens = [wn.lemmatize(word) for word in word_tokenize(desc_visa)]
        return self.tokens
    
    #method to check immigration stance based on description or company (from H1B list)
    def get_immigration_stance(self, comp, companies_list):
        self.immigration = 'Unknown'
        if self.filtered_description == 'check company stance':
            for org in companies_list:
                flag = [] #tracking companies names from H1B list
                if comp.lower() in org.lower() or comp.lower() in org.lower(): flag.append(True)
                if True in flag: self.immigration = 'Yes'
        return self.immigration                    
    
    def collocation_finder(self, n_gram_total, n_gram_filter_word):
        cf = TrigramCollocationFinder.from_words(self.sentence_tokens[0].split()) 
        #checking what words appear frequently with 'word' in this case it is 'work'
        n_filter = lambda *words: n_gram_filter_word not in words
        cf.apply_ngram_filter(n_filter)
        #apply frq filter removes occurences that happened less than x times
        self.collocation_scores = cf.nbest(TrigramAssocMeasures.likelihood_ratio, n_gram_total)
        return self.collocation_scores
    
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
