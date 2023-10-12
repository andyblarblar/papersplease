accounts(_email_, password, first_name, last_name, title, affiliation)

conferences(_id_, name, city, state, country, start_date, end_date, paper_deadline, chair)

papers(_id_, conference_id, title)

paper_authors(_paper_id_, _author_email_)

assignments(_paper_id_, _reviewer_email_, recommendation)

decisions(_paper_id_, status)