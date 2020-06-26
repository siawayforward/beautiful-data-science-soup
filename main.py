import job_postings as job

def main():
    #initiate search and return data table
    t = job.time()
    search = job.New_Postings()
    search.process_retrieved_postings()
    search.save_job_postings()
    job.print_time('Jobs retrieved and saved in {} minutes', t)

if __name__ == '__main__':
    main()
