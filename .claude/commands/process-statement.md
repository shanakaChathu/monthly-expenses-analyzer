# Process a New Expense Statement

This command helps you process a new credit card PDF statement through the
multi-agent pipeline.

## What This Does
1. Asks you which PDF file to process
2. Runs `python main.py --pdf <file>` to trigger the full agent pipeline:
   - PDF Extractor Agent reads and parses the statement
   - Categorizer Agent assigns categories to every transaction
   - Data Manager Agent saves everything to the SQLite database
3. Shows you the processing summary

## Steps

1. First, check if a PDF file exists in the `data/` folder:
   ```bash
   ls data/
   ```

2. If the user hasn't placed a PDF yet, remind them:
   > Place your credit card PDF statement in the `data/` folder.
   > The `data/` folder is gitignored so your personal data stays private.

3. If a PDF is present, run the pipeline:
   ```bash
   python main.py --pdf data/<filename>.pdf
   ```

4. After processing completes, show the summary (saved count, skipped duplicates).

5. Ask the user if they want to launch the dashboard:
   ```bash
   streamlit run dashboard/app.py
   ```

## Notes for the User
- The `data/` folder is in `.gitignore` — your PDFs will never be committed to git.
- Duplicate transactions are automatically skipped if you process the same file twice.
- Each month's data accumulates in `db/expenses.db` (also gitignored).
- Categories are defined in `config/categories.json` — you can customise them.