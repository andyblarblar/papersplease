CREATE TABLE IF NOT EXISTS conferences
(
    id             INT  NOT NULL,
    name           TEXT NOT NULL,
    city           TEXT NOT NULL,
    state          TEXT NOT NULL,
    country        TEXT NOT NULL,
    start_date     DATE NOT NULL,
    end_date       DATE NOT NULL,
    paper_deadline DATE NOT NULL,
    chair          TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (chair) REFERENCES accounts (email)
    );

-- Paper identifiers
CREATE TABLE IF NOT EXISTS papers
(
    id            INT  NOT NULL,
    conference_id INT  NOT NULL,
    title         TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (conference_id) REFERENCES conferences (id) ON UPDATE CASCADE ON DELETE SET NULL
    );

-- Co-authors of papers
CREATE TABLE IF NOT EXISTS paper_authors
(
    paper_id     INT  NOT NULL,
    author_email TEXT NOT NULL,
    PRIMARY KEY (paper_id, author_email),
    FOREIGN KEY (paper_id) REFERENCES papers (id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (author_email) REFERENCES accounts (email) ON UPDATE CASCADE ON DELETE CASCADE
    );

-- Account metadata
-- Note that roles are implicit. Anyone can log in as anything, they just wont see any conferences, papers, assignments etc.
CREATE TABLE IF NOT EXISTS accounts
(
    -- Emails serve as our usernames
    email       TEXT NOT NULL,
    password    TEXT NOT NULL,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    title       TEXT NOT NULL,
    affiliation TEXT NOT NULL,
    PRIMARY KEY (email)
    );

-- Reviewer assignments
CREATE TABLE IF NOT EXISTS assignments
(
    reviewer_email TEXT NOT NULL,
    paper_id       INT  NOT NULL,
    recommendation TEXT NOT NULL CHECK ( recommendation in ('pending', 'accept', 'neutral', 'reject') ) DEFAULT 'pending',
    PRIMARY KEY (reviewer_email, paper_id),
    FOREIGN KEY (reviewer_email) REFERENCES accounts (email) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (paper_id) REFERENCES papers (id) ON UPDATE CASCADE ON DELETE CASCADE
    );

-- Final decisions. These are created by the system when a decision is made, not when one is just recommended
CREATE TABLE IF NOT EXISTS decisions
(
    paper_id INT  NOT NULL,
    status   TEXT NOT NULL CHECK ( status in ('publish', 'do not publish') ),
    PRIMARY KEY (paper_id),
    FOREIGN KEY (paper_id) REFERENCES papers (id) ON UPDATE CASCADE ON DELETE CASCADE
    );