import sqlite3
import json
import requests # For Ollama API calls

DB_FILE = "arxiv_papers.db"
OLLAMA_API_URL = "http://localhost:11434/api/generate" # Default Ollama API endpoint
OLLAMA_MODEL = "llama3" # Model to use

def get_unevaluated_papers(limit=5):
    """Fetches a batch of unevaluated papers from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT arxiv_id, title, abstract, full_text FROM papers WHERE evaluated = 0 LIMIT ?", (limit,))
    papers = cursor.fetchall()
    conn.close()
    return papers

def call_ollama_api(prompt_text):
    """
    Calls the Ollama API with the given prompt.
    Returns the response content or None if an error occurs.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt_text,
        "stream": False # Get the full response at once
    }
    headers = {"Content-Type": "application/json"}

    print(f"\nSending prompt to Ollama (model: {OLLAMA_MODEL}):\n{prompt_text[:300]}... (truncated)")

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, headers=headers, timeout=180) # 3 min timeout
        response.raise_for_status() # Raise an exception for bad status codes
        response_data = response.json()
        print("Ollama API call successful.")
        return response_data.get("response", "").strip()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        print(f"Please ensure Ollama is running and the model '{OLLAMA_MODEL}' is available.")
        print(f"You can run 'ollama run {OLLAMA_MODEL}' in your terminal.")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from Ollama.")
        return None

def parse_llm_response(llm_output_str):
    """
    Parses the LLM's text response to extract structured fields.
    This is a basic parser and might need to be made more robust.
    Expected format:
    YES/NO
    App idea: [Idea]
    Market: [Market]
    MVP idea: [MVP]
    Effort level: [Low/Medium/High]
    Score: [0-50]
    """
    if not llm_output_str:
        return None

    parsed_data = {
        "feasible": None,
        "app_idea": None,
        "market": None,
        "mvp_idea": None,
        "effort_level": None,
        "score": None
    }

    lines = llm_output_str.strip().split('\n')

    if not lines:
        return parsed_data # Return defaults if empty

    # Feasibility (YES/NO)
    first_line_lower = lines[0].lower()
    if "yes" in first_line_lower:
        parsed_data["feasible"] = "YES"
    elif "no" in first_line_lower:
        parsed_data["feasible"] = "NO"

    # Other fields
    for line in lines[1:]: # Start from the second line
        try:
            if ":" in line:
                key, value = line.split(":", 1)
                key_lower = key.lower().strip()
                value_strip = value.strip()

                if "app idea" in key_lower:
                    parsed_data["app_idea"] = value_strip
                elif "market" in key_lower:
                    parsed_data["market"] = value_strip
                elif "mvp idea" in key_lower:
                    parsed_data["mvp_idea"] = value_strip
                elif "effort level" in key_lower:
                    parsed_data["effort_level"] = value_strip
                elif "score" in key_lower:
                    # Try to extract an integer score
                    score_val = ''.join(filter(str.isdigit, value_strip.split(" ")[0])) # Take first part before space if any
                    if score_val:
                        parsed_data["score"] = int(score_val)
        except ValueError:
            print(f"Warning: Could not parse line in LLM output: '{line}'")
            continue # Skip malformed lines

    # If score is still None, try a more general search (e.g., if not prefixed)
    if parsed_data["score"] is None:
        for line in lines:
             if "score" in line.lower() and ":" not in line.lower(): # e.g. "Score 40"
                 score_val = ''.join(filter(str.isdigit, line))
                 if score_val:
                     parsed_data["score"] = int(score_val)
                     break

    # Basic validation for score
    if parsed_data["score"] is not None:
        if not (0 <= parsed_data["score"] <= 50):
            print(f"Warning: LLM returned score {parsed_data['score']} outside 0-50 range. Setting to None.")
            parsed_data["score"] = None # Or clamp, or handle as error

    return parsed_data


def update_paper_evaluation(arxiv_id, score, llm_full_output, parsed_data):
    """Updates the paper's record in the database with evaluation results."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        # Store the structured parsed data as a JSON string for llm_output
        # or individual columns if schema is expanded later.
        # For now, storing the raw llm_full_output and the score.
        # The llm_output column will store the raw text from the LLM.

        cursor.execute('''
        UPDATE papers
        SET evaluated = 1, score = ?, llm_output = ?
        WHERE arxiv_id = ?
        ''', (score, llm_full_output, arxiv_id))
        conn.commit()
        print(f"Updated paper {arxiv_id} with score: {score}")
    except sqlite3.Error as e:
        print(f"SQLite error when updating paper {arxiv_id}: {e}")
    finally:
        conn.close()

def evaluate_papers_from_db(num_to_evaluate=5):
    """
    Main function to fetch, evaluate, and update papers.
    """
    print(f"Starting evaluation for up to {num_to_evaluate} papers...")
    papers_to_evaluate = get_unevaluated_papers(limit=num_to_evaluate)

    if not papers_to_evaluate:
        print("No unevaluated papers found.")
        return

    for paper_row in papers_to_evaluate:
        arxiv_id, title, abstract, full_text = paper_row

        print(f"\n--- Evaluating Paper: {title} ({arxiv_id}) ---")

        # Construct prompt - using title, abstract, and first ~2000 chars of full_text
        # The full_text can be very long, so truncate it.
        # The prompt asks for intro + abstract + conclusion. We'll use abstract + start of full_text.
        text_snippet = abstract if abstract else ""
        if full_text:
            text_snippet += "\n\n[First 2000 chars of Full Text]:\n" + full_text[:2000]
        else:
            text_snippet += "\n\n[Full Text not available or empty]"


        prompt = f"""Analyze this paper and tell if it can be built into a mobile or web app startup. Give:
YES/NO
App idea: [Detailed idea for a web/mobile app]
Market: [Target market and potential users]
MVP idea: [Key features for a Minimum Viable Product]
Effort level: [Low, Medium, or High]
Score: [A numerical score from 0 to 50, where 50 is highest potential]

[Paper Title: {title}]
[Text Snippet:
{text_snippet}
]
"""

        llm_raw_response = call_ollama_api(prompt)

        if llm_raw_response:
            print(f"Raw LLM Response for {arxiv_id}:\n{llm_raw_response}")
            parsed_response = parse_llm_response(llm_raw_response)
            print(f"Parsed LLM Response for {arxiv_id}: {parsed_response}")

            if parsed_response and parsed_response.get("score") is not None:
                update_paper_evaluation(arxiv_id, parsed_response["score"], llm_raw_response, parsed_response)
            elif parsed_response:
                print(f"Could not extract a valid score for {arxiv_id} from LLM response. Storing output without score.")
                update_paper_evaluation(arxiv_id, None, llm_raw_response, parsed_response) # Store output, score as NULL
            else:
                print(f"Could not parse LLM response for {arxiv_id}. Skipping database update for this paper.")
        else:
            print(f"No response from LLM for paper {arxiv_id}. Skipping.")

if __name__ == "__main__":
    # Ensure there's some data in the DB from ingest_arxiv.py first
    # For testing, you might want to manually add a few unevaluated papers or run ingest_arxiv.py

    # Check if DB exists and has papers
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM papers WHERE evaluated = 0")
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0:
        print(f"No unevaluated papers in {DB_FILE}.")
        print("Please run 'python ingest_arxiv.py' first to populate the database.")
        print("If you have run it, ensure some papers passed the filters and are marked as evaluated=0.")
    else:
        print(f"Found {count} unevaluated papers. Starting evaluation...")
        evaluate_papers_from_db(num_to_evaluate=2) # Evaluate 2 papers for a quick test
