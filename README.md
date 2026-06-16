# Fashion Cold Email Personalizer

Reads a CSV of leads, writes a personalised opening line into the "Ps" column using Claude, and saves the result.

**Output line format:**
> Came across your [product] - really clean product and a cool space to be in.

---

## Setup (one-time)

### 1. Create the GitHub repo
1. Go to https://github.com/new
2. Name it `fashion-personalizer` (or whatever you like)
3. Set it to **Private**
4. Click **Create repository**

### 2. Upload these files to the repo
Upload everything in this folder:
- `personalizer.py`
- `requirements.txt`
- `.github/workflows/run.yml`

You can drag and drop them on the GitHub repo page.

### 3. Add your Anthropic API key as a secret
1. In your repo, go to **Settings > Secrets and variables > Actions**
2. Click **New repository secret**
3. Name: `ANTHROPIC_API_KEY`
4. Value: your Anthropic API key (starts with `sk-ant-...`)
5. Click **Add secret**

---

## How to run

### Step 1 — Prepare your CSV
- Make sure your CSV has a column called **`Scrape`** (column S) with the scraped website text
- Make sure it has a column called **`Ps`** (column T) — can be blank
- Name the file **`leads.csv`**
- Upload it to the root of the repo (replace the existing one if there is one)

### Step 2 — Trigger the workflow
1. Go to **Actions** tab in your repo
2. Click **Run Fashion Personalizer** on the left
3. Click **Run workflow** > **Run workflow**
4. Wait for it to finish (green tick)

### Step 3 — Download the output
1. Click on the completed workflow run
2. Scroll down to **Artifacts**
3. Download **leads_output** — this is your CSV with the "Ps" column filled in

---

## Notes
- Rows that already have a value in the "Ps" column are skipped automatically (safe to re-run)
- If a row errors, it writes "ERROR" in that cell so you can spot and retry it
- The script saves progress after every row, so partial runs are not wasted
- Cost: roughly $0.002 per 1,000 rows with claude-sonnet-4-6
