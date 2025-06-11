import sqlite3
import json # For potentially parsing llm_output if needed, not used in current display

DB_FILE = "arxiv_papers.db"
MIN_SCORE_THRESHOLD = 30 # Minimum score to be considered
TOP_N_IDEAS = 20 # Number of top ideas to display

def rank_and_display_top_ideas():
    """
    Queries the database for top-ranked startup ideas and prints them to the console.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print(f"\n--- Top {TOP_N_IDEAS} Startup Ideas (Score >= {MIN_SCORE_THRESHOLD}) ---")

    try:
        cursor.execute(f'''
        SELECT title, score, llm_output
        FROM papers
        WHERE evaluated = 1 AND score >= ?
        ORDER BY score DESC
        LIMIT ?
        ''', (MIN_SCORE_THRESHOLD, TOP_N_IDEAS))

        top_ideas = cursor.fetchall()

        if not top_ideas:
            print("No startup ideas found matching the criteria.")
            print(f"Ensure papers have been evaluated (run evaluate_papers.py) and have scores >= {MIN_SCORE_THRESHOLD}.")
            return

        for i, idea in enumerate(top_ideas):
            title, score, llm_output = idea
            print(f"\n{i+1}. Title: {title}")
            print(f"   Score: {score}")

            # Displaying a snippet of the llm_output
            # In a more advanced version, we might parse the llm_output (JSON)
            # and display specific fields like 'App idea' or 'MVP idea'.
            # For now, just showing the first 150 characters of the raw output.
            output_snippet = llm_output[:150].replace('\n', ' ') + "..." if llm_output else "N/A"
            print(f"   LLM Output Snippet: {output_snippet}")

    except sqlite3.Error as e:
        print(f"SQLite error when querying for top ideas: {e}")
        print(f"Please ensure the database '{DB_FILE}' exists and the 'papers' table is correctly populated.")
    finally:
        conn.close()

if __name__ == "__main__":
    # Check if DB exists and has papers
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM papers WHERE evaluated = 1 AND score IS NOT NULL")
        count = cursor.fetchone()[0]
        if count == 0:
            print(f"No evaluated papers with scores found in {DB_FILE}.")
            print("Please run 'python ingest_arxiv.py' to fetch papers,")
            print("and then 'python evaluate_papers.py' to evaluate them.")
        else:
            print(f"Found {count} evaluated papers with scores. Attempting to rank them...")
            rank_and_display_top_ideas()
    except sqlite3.Error as e:
         print(f"Could not connect to or query database {DB_FILE}: {e}")
         print("Please ensure 'ingest_arxiv.py' has been run to create the database.")
    finally:
        conn.close()
