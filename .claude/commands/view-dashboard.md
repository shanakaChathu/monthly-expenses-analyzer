# Launch the Expenses Dashboard

This command launches the interactive Streamlit dashboard.

## Steps

1. Check that data exists in the database:
   ```bash
   python main.py --list
   ```

2. If no data is found, tell the user to process a statement first:
   ```
   /process-statement
   ```

3. If data exists, launch the dashboard:
   ```bash
   streamlit run dashboard/app.py
   ```

4. Tell the user the dashboard will open at http://localhost:8501 in their browser.

## Dashboard Features
- **Month selector** — switch between any processed month
- **KPI cards** — total spend, transaction count, top category, daily average
- **Monthly trend chart** — bar chart of spend across all months
- **Category pie chart** — breakdown of where money went
- **Top merchants** — highest-spend merchants
- **Transaction table** — searchable, filterable list of all transactions