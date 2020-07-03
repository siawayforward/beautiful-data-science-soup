# beautiful-data-science-soup

A web scrapper that uses beautiful soup to scrape LinkedIn job postings for data analyst/data science positions from the last 24 hours in the U.S. and filters out Virginia jobs (because most of the technology in the state are government contracts), government clearance jobs, and any ones where the description explicitly states that there is no visa assistance or E-Verify program with the position. There is no model that generates the outcome. Additionally, the program also scrapes <https://www.myvisajobs.com/> to find out which companies automatically will provide assistance based on the current year's practices of the organization. Most of the filtering is done using some cool modules from nltk including collocation finder classes, n-gram filtering, and wordninja - a package that checks for misspelling and conjoined words e.g. wordninja -> word ninja

***Goal*** = practice web scrapping and NLTK tools for natural language processing with Python

## Pre-requisite non-standard packages

- NLTK
- Beautiful Soup 4
- wordninja

### Instructions

- Download and save `job_postings.py`, `job_description.py`, `job_titles.txt`, and the `main.py` file to the same directory
- Run `main.py`. Process will display on terminal, and once completed, an excel file will be saved to the same directory where the other scripts are located.
- **Note:** Since the job titles file is not hard-coded, you can change the search titles to match another set of positions of interest/industry
- The program takes between 3 and 5 minutes to run. This is an ongoing inefficiency that will be fixed; currently learning how to use scrapy to replace with for faster computation
- Excel file will include positions sorted by 'yes' -> 'unknown' -> 'no' sponsorship or assistance so that those needed are seen first. The first check showed only 65-70% accuracy in prediction without a model.
- ***Also note***, positions labeled as *unknown* may be from companies that are not clear enough in the description (e.g. no mention of E-verify or visas, but also no denials), OR an inaccurate conclusion.
- When you open the excel file, click on the job title to navigate to the job link. There are some links with issues. This is addressed below.

**Ongoing Improvements:**

- Modeling the tfidf vectors from the filtered descriptions
- Checking for years of experience phrases to filter out junior or entry level positions
- Customizing location within the U.S. (but COVID-19 is here so we can't be too picky right now!)
- Mail to an email list every day
- Correct excel hyperlinks

<span style="color:red">some **Known Issues** </span>

Some job links have issues so the HYPERLINK excel function does not work when the file is opened. You might get a prompt asking if you want to keep some sources that are harmful. This means there is a broken link. Press 'yes' and proceed for now. There will not be links on those particular items. This is being fixed currently.
