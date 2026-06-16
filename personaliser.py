import os
import time
import pandas as pd
import anthropic

# ── CONFIG ──────────────────────────────────────────────────────────────────
INPUT_CSV = "leads_brendon.csv"          # CSV file you upload to the repo before running
OUTPUT_CSV = "leads_output.csv"  # Updated CSV written after the run
COL_SCRAPE = "Scrape"            # Column S — scraped website text
COL_OUTPUT = "Ps"                # Column T — personalized line output
DELAY_BETWEEN_ROWS = 2           # Seconds between Claude API calls
CLAUDE_MODEL = "claude-sonnet-4-6"
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


def generate_line(client: anthropic.Anthropic, scrape_text: str) -> str:
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=100,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": build_user_prompt(scrape_text)}
        ]
    )
    return message.content[0].text.strip()


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set.")

    client = anthropic.Anthropic(api_key=api_key)

    df = pd.read_csv(INPUT_CSV)

    # Make sure the output column exists
    if COL_OUTPUT not in df.columns:
        df[COL_OUTPUT] = ""

    # Convert to string and strip whitespace so empty-check works cleanly
    df[COL_SCRAPE] = df[COL_SCRAPE].fillna("").astype(str).str.strip()
    df[COL_OUTPUT] = df[COL_OUTPUT].fillna("").astype(str).str.strip()

    rows_to_process = df[
        (df[COL_SCRAPE] != "") & (df[COL_OUTPUT] == "")
    ].index.tolist()

    print(f"Rows to process: {len(rows_to_process)}")

    for i, idx in enumerate(rows_to_process):
        scrape_text = df.at[idx, COL_SCRAPE]
        brand = df.at[idx, "Brand"] if "Brand" in df.columns else f"Row {idx + 1}"

        print(f"[{i + 1}/{len(rows_to_process)}] Processing: {brand}")

        try:
            line = generate_line(client, scrape_text)
            df.at[idx, COL_OUTPUT] = line
            print(f"  => {line}")
        except Exception as e:
            print(f"  ERROR: {e}")
            df.at[idx, COL_OUTPUT] = "ERROR"

        # Save after every row so progress is not lost if something fails mid-run
        df.to_csv(OUTPUT_CSV, index=False)

        if i < len(rows_to_process) - 1:
            time.sleep(DELAY_BETWEEN_ROWS)

    print(f"\nDone. Output saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
