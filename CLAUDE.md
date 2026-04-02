# Monthly Expenses Analyzer — Claude Code Instructions

## Project Overview
An AI-powered multi-agent system that reads credit card PDF statements,
extracts and categorizes transactions, and displays them in an interactive
Streamlit dashboard.

## Architecture — Multi-Agent System

```
User uploads PDF
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                       │
│  (claude-opus-4-6 with adaptive thinking + tool use)│
│  agents/orchestrator.py                             │
└──────┬──────────────┬──────────────┬────────────────┘
       │              │              │
       ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│PDF EXTRACTOR│ │CATEGORIZER │ │DATA MANAGER│
│   Agent    │ │   Agent    │ │   Agent    │
│(claude-opus)│ │(claude-opus)│ │  (SQLite)  │
└────────────┘ └────────────┘ └────────────┘
       │              │              │
       └──────────────┴──────────────┘
                      │
                      ▼
             ┌─────────────────┐
             │   DASHBOARD     │
             │ dashboard/app.py│
             │  (Streamlit +   │
             │   Plotly)       │
             └─────────────────┘
```

### Agents Explained
- **Orchestrator** (`agents/orchestrator.py`): Uses Claude with tool_use to
  coordinate the pipeline. It calls sub-agents as tools and decides the
  processing order. This is where you learn about agentic behavior.

- **PDF Extractor** (`agents/pdf_extractor.py`): Uses pdfplumber to read the
  PDF, then passes the raw text to Claude to intelligently extract transactions
  as structured JSON.

- **Categorizer** (`agents/categorizer.py`): Takes raw transactions and uses
  Claude to assign categories (Food & Dining, Transport, etc.) based on
  merchant names and descriptions.

- **Data Manager** (`agents/data_manager.py`): Handles all SQLite database
  operations — saving, querying, deduplication.

## How to Run

### Setup (first time only)
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Process a New Statement
```bash
# Place your PDF in the data/ folder (gitignored for privacy)
python main.py --pdf data/adcb_march.pdf

# With a custom label
python main.py --pdf data/adcb_march.pdf --label "March 2024"
```

### Launch Dashboard
```bash
streamlit run dashboard/app.py
```

## Slash Commands (Claude Code)
These are custom commands you can invoke in Claude Code:
- `/process-statement` — Walk through processing a new PDF statement
- `/view-dashboard` — Launch the Streamlit dashboard
- `/add-category` — Add a new expense category to the config

## Key Files
| File | Purpose |
|------|---------|
| `config/categories.json` | Expense categories and keywords |
| `agents/orchestrator.py` | Multi-agent coordinator |
| `agents/pdf_extractor.py` | PDF → structured transactions |
| `agents/categorizer.py` | Transactions → categories |
| `agents/data_manager.py` | SQLite read/write |
| `prompts/system_prompts.py` | All Claude system prompts |
| `dashboard/app.py` | Interactive Streamlit dashboard |
| `db/expenses.db` | SQLite database (gitignored) |
| `data/` | PDF storage (gitignored — private) |

## Adding New Categories
Edit `config/categories.json` to add a new category:
```json
{
  "name": "Your Category",
  "color": "#hexcolor",
  "keywords": ["keyword1", "keyword2"]
}
```
The Categorizer agent uses these keywords as hints when classifying.

## Database Schema
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'AED',
    transaction_type TEXT DEFAULT 'debit',
    category TEXT NOT NULL,
    subcategory TEXT,
    month TEXT NOT NULL,
    year INTEGER NOT NULL,
    source_file TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, description, amount)
);
```

## Development Guidelines
- **Never commit PDF files** — they contain personal financial data
- **Never commit `db/expenses.db`** — it contains your transaction history
- **Never commit `.env`** — it contains your API key
- All monetary amounts are stored in AED (UAE Dirhams)
- Dates are stored as ISO format strings (YYYY-MM-DD)
- The Orchestrator uses `claude-opus-4-6` with `thinking: {type: "adaptive"}`
- Sub-agents use `claude-opus-4-6` for their AI tasks

## Learning Goals (Multi-Agent Concepts)
This project demonstrates:
1. **Tool use** — Orchestrator uses Claude's tool_use to call sub-agents
2. **Agentic loop** — Manual loop that runs until `stop_reason == "end_turn"`
3. **Specialized agents** — Each agent has a focused responsibility
4. **System prompts** — Each agent has a tailored system prompt
5. **Structured outputs** — Agents return JSON for inter-agent communication
6. **CLAUDE.md** — This file! Gives Claude Code context about the project
7. **Slash commands** — `.claude/commands/*.md` files for custom workflows
