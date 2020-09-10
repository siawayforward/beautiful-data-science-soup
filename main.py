import job_postings as job

def main():
    #initiate search and return data table
    t = job.time()
    print()
    search = job.New_Postings()
    search.process_retrieved_postings()
    search.get_job_postings()
    #search.save_job_postings()
    job.print_time('Time - jobs retrieved and saved:', t)
    print()

if __name__ == '__main__':
    main()
