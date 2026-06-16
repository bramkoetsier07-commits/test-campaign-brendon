import os
import time
import pandas as pd
from openai import OpenAI, RateLimitError
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── CONFIG ──────────────────────────────────────────────────────────────────
INPUT_CSV = "leads.csv"          # CSV file you upload to the repo before running
OUTPUT_CSV = "leads_output.csv"  # Updated CSV written after the run
COL_SCRAPE = "Scrape"            # Column S — scraped website text
COL_OUTPUT = "Ps"                # Column T — personalized line output
GPT_MODEL = "gpt-5-mini"         # Confirmed model string from OpenAI docs
MAX_WORKERS = 10                 # Number of parallel API calls (safe for Tier 1+)
MAX_RETRIES = 4                  # Retries per row if rate limited
SAVE_EVERY = 50                  # Save progress to CSV every N rows completed
# ────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a cold email personalization transformer.

Your job: extract the core product from scraped website text and write one sentence in this exact format:
Came across your [PRODUCT] - really clean product and a cool space to be in.

Rules you must never break:
- Always start with "Came across your"
- Always use a hyphen " - " after the product
- Always end with "really clean product and a cool space to be in."
- Output only one single sentence, nothing else
- No quotes around the output
- No emojis
- Max 3 words for the product/category
- Use simple, everyday words (say "horse supplements" not "equine supplements", say "weight loss pills" not "metabolic optimization supplements")
- Never use "and" to join two products - pick only the single most obvious one
- No descriptive prefixes - use the core product name only (say "supplements" not "performance recovery supplements", say "face cream" not "physician-approved anti-aging moisturizer")
- The product phrase must sound natural inside the sentence"""


def build_user_prompt(scrape_text: str) -> str:
    return f"""Scraped website text:
{scrape_text}

Write the personalized line now."""


def generate_line(client: OpenAI, scrape_text: str) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                max_tokens=100,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(scrape_text)}
                ]
            )
            return response.choices[0].message.content.strip()
        except RateLimitError:
            wait = 2 ** attempt  # 1s, 2s, 4s, 8s
            print(f"  Rate limited — waiting {wait}s before retry...")
            time.sleep(wait)
    return "ERROR: rate limit exceeded after retries"


def process_row(args):
    idx, scrape_text, brand, client = args
    try:
        line = generate_line(client, scrape_text)
        return idx, line, None
    except Exception as e:
        return idx, "ERROR", str(e)


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    client = OpenAI(api_key=api_key)

    df = pd.read_csv(INPUT_CSV)

    if COL_OUTPUT not in df.columns:
        df[COL_OUTPUT] = ""

    df[COL_SCRAPE] = df[COL_SCRAPE].fillna("").astype(str).str.strip()
    df[COL_OUTPUT] = df[COL_OUTPUT].fillna("").astype(str).str.strip()

    rows_to_process = df[
        (df[COL_SCRAPE] != "") & (df[COL_OUTPUT] == "")
    ].index.tolist()

    total = len(rows_to_process)
    print(f"Rows to process: {total}")
    print(f"Running {MAX_WORKERS} parallel workers — estimated time: ~{round(total / (MAX_WORKERS / 1.5) / 60)} min\n")

    completed = 0
    start_time = time.time()

    tasks = [
        (idx, df.at[idx, COL_SCRAPE], df.at[idx, "Brand"] if "Brand" in df.columns else f"Row {idx+1}", client)
        for idx in rows_to_process
    ]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_row, task): task[0] for task in tasks}

        for future in as_completed(futures):
            idx, line, error = future.result()
            df.at[idx, COL_OUTPUT] = line
            completed += 1

            if error:
                print(f"[{completed}/{total}] Row {idx} ERROR: {error}")
            else:
                brand = df.at[idx, "Brand"] if "Brand" in df.columns else f"Row {idx+1}"
                print(f"[{completed}/{total}] {brand} => {line}")

            # Save every N rows so progress is not lost
            if completed % SAVE_EVERY == 0 or completed == total:
                df.to_csv(OUTPUT_CSV, index=False)
                elapsed = round((time.time() - start_time) / 60, 1)
                print(f"  -- Saved. {completed}/{total} done ({elapsed} min elapsed) --")

    df.to_csv(OUTPUT_CSV, index=False)
    elapsed = round((time.time() - start_time) / 60, 1)
    print(f"\nDone. {total} rows processed in {elapsed} min. Output saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
