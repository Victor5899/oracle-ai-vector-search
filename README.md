# Oracle AI Vector Search – Smart Document Q&A System

A document question-and-answer system that uses **Oracle AI Vector Search** to store embeddings and retrieve relevant content for user queries.

## Project Structure

```
oracle-ai-vector-search/
├── README.md
├── .gitignore
├── requirements.txt
├── src/          # Python application / backend code
├── sql/          # Oracle SQL and PL/SQL
├── data/         # Sample and input documents
├── docs/         # Project documentation, diagrams, and reports
└── app/          # Future user interface
```

## Prerequisites

- Python 3.10 or later
- Access to an Oracle Database with AI Vector Search support
- pip (or another Python package installer)

## Setup

1. Clone or copy this repository, then move into the project directory:

   ```bash
   cd oracle-ai-vector-search
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure database and environment settings when they are added later in development.

## Status

This repository currently contains the project baseline only. Application code, SQL scripts, sample data, documentation, and the user interface will be added as development progresses.
