# ArXiv Startup Idea Mining Tool

This project is a tool to fetch research papers from arXiv, use a local Large Language Model (LLM) via Ollama to evaluate their potential for web/mobile app startup ideas, and then rank these ideas.

## Features

-   Fetches papers from arXiv based on specified queries.
-   Extracts text content from PDF papers.
-   Stores paper metadata and text in a local SQLite database.
-   Filters papers based on AI categories and equation count.
-   Uses a local LLM (via Ollama) to evaluate startup feasibility, suggest app ideas, markets, MVPs, effort levels, and assign a score.
-   Ranks and displays the top startup ideas.
-   Provides a Command Line Interface (CLI) to manage the workflow.

## Project Structure

```
arxiv_startup_miner/
├── pdfs/                     # Downloaded PDF papers (gitignored)
├── arxiv_papers.db           # SQLite database (gitignored)
├── ingest_arxiv.py           # Script for fetching and storing arXiv papers
├── evaluate_papers.py        # Script for LLM evaluation using Ollama
├── rank_ideas.py             # Script for ranking and displaying ideas
├── cli.py                    # Main command-line interface for the tool
├── .gitignore                # Specifies intentionally untracked files
└── README.md                 # This file
```

## Prerequisites

1.  **Python 3.7+**: Ensure you have Python installed.
2.  **Ollama**: You need Ollama installed and running with a model.
    -   Download and install Ollama from [ollama.com](https://ollama.com/).
    -   Pull a model that will be used for evaluation (e.g., Llama 3):
        ```bash
        ollama pull llama3
        ```
    -   Ensure Ollama is serving on its default address (`http://localhost:11434`). The script `evaluate_papers.py` uses this address and the `llama3` model by default. You can change `OLLAMA_API_URL` and `OLLAMA_MODEL` constants in the script if needed.

## Setup

1.  **Clone the repository (or set up the files):**
    If this were a git repository, you'd clone it. For now, ensure all the Python scripts (`ingest_arxiv.py`, `evaluate_papers.py`, `rank_ideas.py`, `cli.py`) are in a directory named `arxiv_startup_miner`.

2.  **Install Python dependencies:**
    Navigate to the project directory (`arxiv_startup_miner/`) in your terminal and install the required libraries:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The primary way to use the tool is through `cli.py`.

```bash
cd arxiv_startup_miner
python cli.py --help
```

This will show you the available commands and their options.

### Step 1: Ingest Papers

Fetch papers from arXiv, process them, and store them in the local SQLite database (`arxiv_papers.db`). The `pdfs/` directory will be created to store downloaded PDFs.

```bash
python cli.py ingest --query "cat:cs.AI OR cat:cs.LG" --max_papers 20
```
-   `--query`: (Optional) ArXiv query. Default: `"cat:cs.AI OR cat:cs.LG OR cat:stat.ML"`
-   `--max_papers`: (Optional) Max number of papers to fetch and process after filtering. Default: `10`

This command will create `arxiv_papers.db` if it doesn't exist.

### Step 2: Evaluate Papers

Use the configured Ollama LLM to evaluate papers stored in the database that haven't been evaluated yet.

```bash
python cli.py evaluate --num_to_evaluate 10
```
-   `--num_to_evaluate`: (Optional) Max number of papers to evaluate in this run. Default: `5`

Make sure Ollama is running with the required model (`llama3` by default) before running this command.

### Step 3: Rank and View Ideas

Display the top-ranked startup ideas based on the LLM scores.

```bash
python cli.py rank
```
This will show the top 20 ideas with a score of 30 or more by default (as defined in `rank_ideas.py`).

## Development Notes

-   **LLM Prompting**: The prompt used for Ollama is defined in `evaluate_papers.py`. You can modify it to change how the LLM evaluates papers.
-   **LLM Response Parsing**: The `parse_llm_response` function in `evaluate_papers.py` is crucial. It's designed for a specific output format. If your LLM model provides responses in a different structure, this function will need to be updated.
-   **Filtering**: Paper filtering logic (categories, equation count) is in `ingest_arxiv.py`.
-   **Database**: The schema is defined in `ingest_arxiv.py`. If you add new fields to store from the LLM, you'll need to update the schema and relevant parts of `evaluate_papers.py`.

## .gitignore

The `.gitignore` file is set up to exclude:
-   Python cache files (`__pycache__/`, `*.pyc`, etc.)
-   The `pdfs/` directory.
-   Database files (`*.db`, `*.sqlite3`, `*.json` (legacy)).
-   Virtual environment folders (`env/`, `venv/`).
-   OS-specific files (`.DS_Store`, `Thumbs.db`).
