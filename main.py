"""
Monthly Expenses Analyzer — CLI Entry Point
--------------------------------------------
Usage:
    python main.py --pdf data/adcb_march.pdf
    python main.py --pdf data/adcb_march.pdf --label "March 2024"
    python main.py --dashboard        (launches Streamlit)
    python main.py --list             (show all stored months)
"""

import argparse
import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()


def check_api_key():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        print("  1. Copy .env.example to .env")
        print("  2. Add your API key to .env")
        sys.exit(1)


def process_pdf(pdf_path: str, label: str | None = None):
    """Run the full multi-agent pipeline on a PDF statement."""
    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    check_api_key()

    # Import here so missing deps give a clear error
    from agents.orchestrator import OrchestratorAgent

    agent = OrchestratorAgent()
    summary = agent.process_statement(pdf_path)

    print("\n" + "=" * 50)
    print("  PROCESSING COMPLETE")
    print("=" * 50)
    if summary.get("saved") is not None:
        print(f"  New transactions saved : {summary['saved']}")
        print(f"  Duplicates skipped     : {summary['skipped']}")
        print(f"  Total processed        : {summary['total']}")
    if summary.get("message"):
        print(f"\n{summary['message']}")
    print("\nTo view your dashboard:")
    print("  streamlit run dashboard/app.py")
    print("=" * 50)


def launch_dashboard():
    """Launch the Streamlit dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "app.py")
    print("Launching dashboard...")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", dashboard_path],
        check=False,
    )


def list_months():
    """Print a summary of all months in the database."""
    from agents import data_manager as dm

    months = dm.get_available_months()
    if not months:
        print("No data found. Run 'python main.py --pdf <file>' first.")
        return

    print("\nMonths with data:")
    print("-" * 30)
    for m in months:
        rows = dm.get_transactions_by_month(m["month"], m["year"])
        debits = [r for r in rows if r.get("transaction_type") == "debit"]
        total = sum(r["amount"] for r in debits)
        print(f"  {m['month']} {m['year']}: {len(debits)} transactions, AED {total:,.0f}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Monthly Expenses Analyzer — Multi-Agent Expense Tracker"
    )
    parser.add_argument(
        "--pdf",
        metavar="PATH",
        help="Path to a credit card PDF statement to process",
    )
    parser.add_argument(
        "--label",
        metavar="LABEL",
        help='Optional label for the statement (e.g. "March 2024")',
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the interactive Streamlit dashboard",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all months stored in the database",
    )

    args = parser.parse_args()

    if args.pdf:
        process_pdf(args.pdf, args.label)
    elif args.dashboard:
        launch_dashboard()
    elif args.list:
        list_months()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
