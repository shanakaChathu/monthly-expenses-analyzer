# Monthly Expenses Analyzer

An AI-powered **multi-agent** system that reads credit card PDF statements,
categorizes transactions intelligently, and displays everything in an
interactive dashboard.

Built to learn multi-agent patterns with the **Anthropic Claude API**.

---

## Architecture

```
PDF Statement
     │
     ▼
┌─────────────────────────────────────┐
│          ORCHESTRATOR               │
│  claude-opus-4-6 + adaptive thinking│
│  Coordinates agents via tool_use   │
└──────┬──────────┬──────────┬────────┘
       │          │          │
       ▼          ▼          ▼
  PDF Extractor  Categorizer  Data Manager
  (Claude)       (Claude)     (SQLite)
       │          │          │
       └──────────┴──────────┘
                  │
                  ▼
         Streamlit Dashboard
         (Plotly charts)
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up your API key
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=sk-ant-...

# 3. Process a statement (place your PDF in data/)
python main.py --pdf data/adcb_march.pdf

# 4. Launch the dashboard
streamlit run dashboard/app.py
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `python main.py --pdf data/file.pdf` | Process a new PDF statement |
| `python main.py --list` | Show all months with data |
| `python main.py --dashboard` | Launch the Streamlit dashboard |
| `streamlit run dashboard/app.py` | Launch dashboard directly |

## Claude Code Slash Commands

| Command | Description |
|---------|-------------|
| `/process-statement` | Guided workflow to process a new statement |
| `/view-dashboard` | Launch the interactive dashboard |
| `/add-category` | Add a new expense category |

## Project Structure

```
monthly_expenses_analyzer/
├── CLAUDE.md                    # Claude Code project instructions
├── main.py                      # CLI entry point
├── requirements.txt
├── .env.example
├── config/
│   └── categories.json          # Expense categories & keywords
├── agents/
│   ├── orchestrator.py          # Multi-agent coordinator (tool_use loop)
│   ├── pdf_extractor.py         # PDF → JSON transactions (Claude)
│   ├── categorizer.py           # Transactions → categories (Claude)
│   └── data_manager.py          # SQLite read/write
├── prompts/
│   └── system_prompts.py        # All Claude system prompts
├── dashboard/
│   └── app.py                   # Streamlit interactive dashboard
├── data/                        # PDFs go here (gitignored)
└── db/                          # SQLite database (gitignored)
```

## Multi-Agent Concepts Demonstrated

| Concept | Where |
|---------|-------|
| **Tool use** | `orchestrator.py` — Claude calls sub-agents as tools |
| **Agentic loop** | `orchestrator.py` — loop until `stop_reason == "end_turn"` |
| **Adaptive thinking** | `pdf_extractor.py` — `thinking: {type: "adaptive"}` |
| **Specialized agents** | Each agent has one focused job |
| **Structured outputs** | Agents return JSON for inter-agent communication |
| **System prompts** | `prompts/system_prompts.py` — one prompt per agent |
| **CLAUDE.md** | Project instructions loaded automatically by Claude Code |
| **Slash commands** | `.claude/commands/*.md` — custom `/process-statement` etc. |

## Privacy

- `data/` and `db/` are gitignored — your PDFs and transaction history are never committed
- Your `.env` (API key) is also gitignored

## License

MIT