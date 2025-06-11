import arxiv
import fitz # PyMuPDF
import os
import sqlite3
import json # Keep for authors/categories list to string conversion

# --- Constants ---
PDF_DIR = "pdfs"
DB_FILE = "arxiv_papers.db"
MAX_EQUATIONS = 10 # Max number of equations allowed
AI_CATEGORIES = {'cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.NE', 'stat.ML'} # Set for efficient lookup

# --- Database Functions ---
def init_db():
    """Initializes the SQLite database and creates the papers table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS papers (
        arxiv_id TEXT PRIMARY KEY,
        title TEXT,
        abstract TEXT,
        authors TEXT, -- Store as JSON string
        categories TEXT, -- Store as JSON string
        pdf_url TEXT,
        published TEXT,
        full_text TEXT,
        evaluated INTEGER DEFAULT 0,
        score INTEGER,
        llm_output TEXT
    )
    ''')
    conn.commit()
    conn.close()

def store_in_db(paper_data):
    """Stores paper data into the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT OR REPLACE INTO papers
        (arxiv_id, title, abstract, authors, categories, pdf_url, published, full_text, evaluated, score, llm_output)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            paper_data['arxiv_id'],
            paper_data['title'],
            paper_data['abstract'],
            json.dumps(paper_data['authors']), # Convert list to JSON string
            json.dumps(paper_data['categories']), # Convert list to JSON string
            paper_data['pdf_url'],
            paper_data['published'],
            paper_data['full_text'],
            paper_data.get('evaluated', 0), # Default to 0 if not provided
            paper_data.get('score', None),   # Default to None
            paper_data.get('llm_output', None) # Default to None
        ))
        conn.commit()
        print(f"Stored/Updated {paper_data['arxiv_id']} in {DB_FILE}")
    except sqlite3.Error as e:
        print(f"SQLite error when storing {paper_data['arxiv_id']}: {e}")
    finally:
        conn.close()

# --- PDF and arXiv Functions ---
def extract_pdf_text(pdf_path):
    """Extracts full text from a PDF file."""
    try:
        with fitz.open(pdf_path) as doc:
            text = "".join(page.get_text() for page in doc)
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""

def fetch_and_store_papers(query="cat:cs.LG", max_results=20): # Increased default for better filtering test
    """Fetches papers from arXiv, filters them, downloads PDFs, extracts text, and stores them."""
    print(f"Fetching up to {max_results} papers for query '{query}'...")

    # Ensure PDF directory exists
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR)

    search = arxiv.Search(
        query=query,
        max_results=max_results, # Fetch more to have enough papers after filtering
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    results = list(search.results())
    if not results:
        print("No papers found for the query.")
        return

    processed_count = 0
    for paper in results:
        if processed_count >= max_results: # Ensure we don't exceed max_results after filtering
            break

        arxiv_id = paper.entry_id.split('/')[-1]
        print(f"\nProcessing paper: {paper.title} ({arxiv_id})")

        # Pre-filter by category
        paper_categories = set(paper.categories)
        if not AI_CATEGORIES.intersection(paper_categories):
            print(f"Skipping paper {arxiv_id} due to category mismatch. Categories: {paper_categories}")
            continue

        print(f"Paper categories {paper_categories} accepted.")

        # Download PDF
        pdf_filename = f"{arxiv_id}.pdf"
        pdf_path = os.path.join(PDF_DIR, pdf_filename)

        try:
            print(f"Downloading PDF to {pdf_path}...")
            # Check if PDF already exists to save download time during testing
            if not os.path.exists(pdf_path):
                 paper.download_pdf(dirpath=PDF_DIR, filename=pdf_filename)
                 print("Download complete.")
            else:
                 print("PDF already exists. Skipping download.")

            # Extract text
            print("Extracting text...")
            full_text = extract_pdf_text(pdf_path)
            if not full_text:
                print(f"Could not extract text from {pdf_path}. Skipping.")
                continue
            print(f"Extracted ~{len(full_text)} characters.")

            # Pre-filter by equation count
            equation_count = full_text.lower().count("begin{equation}") # Check in lower to be safe
            if equation_count > MAX_EQUATIONS:
                print(f"Skipping paper {arxiv_id} due to high equation count: {equation_count}")
                continue
            print(f"Equation count: {equation_count} (within limit).")

            # Prepare data for storage
            paper_info = {
                "arxiv_id": arxiv_id,
                "title": paper.title,
                "abstract": paper.summary,
                "authors": [author.name for author in paper.authors],
                "categories": paper.categories,
                "pdf_url": paper.pdf_url,
                "published": paper.published.isoformat(),
                "full_text": full_text
            }

            # Store in DB
            store_in_db(paper_info)
            processed_count +=1

        except Exception as e:
            print(f"An error occurred processing paper {arxiv_id}: {e}")

    print(f"\nFinished processing. Stored {processed_count} papers matching criteria.")

if __name__ == "__main__":
    init_db() # Initialize DB and table

    # Example usage: Fetch more to see filtering in action
    fetch_and_store_papers(query="cat:cs.* OR cat:stat.ML", max_results=5) # Fetch 5 papers from CS and stat.ML

    # Verify content of SQLite DB
    print("\n--- Content of Database (first 5 papers) ---")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT arxiv_id, title, categories, evaluated, score FROM papers LIMIT 5")
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                print(f"ID: {row[0]}, Title: {row[1]}, Categories: {json.loads(row[2])}, Evaluated: {row[3]}, Score: {row[4]}")
        else:
            print("No papers found in the database.")
    except sqlite3.Error as e:
        print(f"Error querying database: {e}")
    finally:
        conn.close()

    print("\n--- Schema of 'papers' table ---")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(papers)")
        schema_info = cursor.fetchall()
        if schema_info:
            print("Column Name | Data Type | Not Null | Default Value | Primary Key")
            print("-------------------------------------------------------------------")
            for col in schema_info:
                print(f"{col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
        else:
            print("Could not retrieve schema information for 'papers' table.")
    except sqlite3.Error as e:
        print(f"Error querying schema: {e}")
    finally:
        conn.close()
