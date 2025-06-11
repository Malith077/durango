import argparse
import os
import sqlite3 # Needed for db checks in cli

# Import functions from other modules
# Need to make sure Python can find them. If run as `python arxiv_startup_miner/cli.py` from parent dir, this should work.
# Otherwise, PYTHONPATH adjustments or packaging would be needed for more complex setups.
from ingest_arxiv import init_db as init_ingest_db, fetch_and_store_papers
from evaluate_papers import evaluate_papers_from_db
from rank_ideas import rank_and_display_top_ideas

DB_FILE = "arxiv_papers.db" # Centralize DB file reference

def check_db_initialized():
    """Checks if the database exists and has the 'papers' table."""
    if not os.path.exists(DB_FILE):
        return False
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='papers';")
        if cursor.fetchone() is None:
            return False # Table doesn't exist
    except sqlite3.Error:
        return False # DB might be corrupt or not a DB file
    finally:
        conn.close()
    return True

def main():
    parser = argparse.ArgumentParser(description="ArXiv Startup Idea Mining Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Fetch papers from arXiv and store them")
    ingest_parser.add_argument("--query", type=str, default="cat:cs.AI OR cat:cs.LG OR cat:stat.ML", help="ArXiv query string (default: 'cat:cs.AI OR cat:cs.LG OR cat:stat.ML')")
    ingest_parser.add_argument("--max_papers", type=int, default=10, help="Maximum number of papers to fetch and process (default: 10)")

    # Evaluate command
    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate stored papers using Ollama")
    evaluate_parser.add_argument("--num_to_evaluate", type=int, default=5, help="Maximum number of papers to evaluate in this run (default: 5)")

    # Rank command
    rank_parser = subparsers.add_parser("rank", help="Rank and display top startup ideas")
    # rank_parser.add_argument("--top_n", type=int, default=20, help="Number of top ideas to display (default: 20)") # rank_ideas.py already has TOP_N_IDEAS constant
    # rank_parser.add_argument("--min_score", type=int, default=30, help="Minimum score for ideas to be displayed (default: 30)") # rank_ideas.py already has MIN_SCORE_THRESHOLD

    args = parser.parse_args()

    # Ensure DB is initialized for all commands that need it.
    # For 'ingest', it will initialize it. For others, it should exist.
    if args.command != "ingest" and not check_db_initialized():
        print(f"Database '{DB_FILE}' not found or not initialized.")
        print("Please run the 'ingest' command first to create and populate the database.")
        return

    if args.command == "ingest":
        print("Starting paper ingestion process...")
        init_ingest_db() # Ensure table exists
        fetch_and_store_papers(query=args.query, max_results=args.max_papers)
        print("Ingestion process finished.")

    elif args.command == "evaluate":
        print("Starting LLM evaluation process...")
        evaluate_papers_from_db(num_to_evaluate=args.num_to_evaluate)
        print("Evaluation process finished.")

    elif args.command == "rank":
        print("Ranking and displaying top ideas...")
        rank_and_display_top_ideas()
        print("Ranking display finished.")

if __name__ == "__main__":
    main()
