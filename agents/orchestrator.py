"""
Orchestrator Agent
------------------
The top-level agent that coordinates the full expense processing pipeline.

This is where you see multi-agent behaviour in action:

  Claude (claude-opus-4-6 with adaptive thinking) acts as the "brain".
  It decides which tools (sub-agents) to call and in what order.
  The manual agentic loop runs until Claude signals it is done.

Tool flow:
  1. extract_transactions   → PDFExtractorAgent
  2. categorize_transactions → CategorizerAgent
  3. save_transactions       → DataManagerAgent

Learning notes:
  - "tool_use" blocks in the response mean Claude wants to call a tool.
  - We execute the tool, then feed back a "tool_result" message.
  - The loop continues until stop_reason == "end_turn".
  - adaptive thinking lets Claude reason carefully about ambiguous steps.
"""

import json
import os

import anthropic
from dotenv import load_dotenv

from agents.pdf_extractor import PDFExtractorAgent
from agents.categorizer import CategorizerAgent
from agents import data_manager as dm
from prompts.system_prompts import ORCHESTRATOR_SYSTEM_PROMPT

load_dotenv()


# ---------------------------------------------------------------------------
# Tool definitions (passed to Claude so it knows what it can call)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "extract_transactions",
        "description": (
            "Extract all financial transactions from a credit card PDF statement. "
            "Call this first with the path to the PDF file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pdf_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the PDF file.",
                }
            },
            "required": ["pdf_path"],
        },
    },
    {
        "name": "categorize_transactions",
        "description": (
            "Assign expense categories to a list of raw transactions. "
            "Call this after extract_transactions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transactions": {
                    "type": "array",
                    "description": "List of transaction objects from extract_transactions.",
                    "items": {"type": "object"},
                }
            },
            "required": ["transactions"],
        },
    },
    {
        "name": "save_transactions",
        "description": (
            "Persist categorized transactions to the database. "
            "Call this after categorize_transactions. "
            "Returns a summary with saved/skipped counts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transactions": {
                    "type": "array",
                    "description": "Categorized transaction objects.",
                    "items": {"type": "object"},
                },
                "source_file": {
                    "type": "string",
                    "description": "Name of the source PDF file for tracking.",
                },
            },
            "required": ["transactions"],
        },
    },
]


class OrchestratorAgent:
    """
    Coordinates the multi-agent pipeline using Claude's tool_use feature.

    The orchestrator itself is powered by claude-opus-4-6 with adaptive
    thinking, which lets it reason step-by-step through the pipeline.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-opus-4-6"

        # Sub-agents
        self.pdf_extractor = PDFExtractorAgent()
        self.categorizer = CategorizerAgent()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def process_statement(self, pdf_path: str) -> dict:
        """
        Full pipeline: PDF → extract → categorize → save → summary.

        Args:
            pdf_path: Path to the credit card PDF statement.

        Returns:
            A summary dict describing what was processed.
        """
        pdf_path = os.path.abspath(pdf_path)
        source_file = os.path.basename(pdf_path)

        print(f"\n[Orchestrator] Starting pipeline for: {source_file}")
        print("[Orchestrator] Asking Claude to coordinate the agents...\n")

        messages = [
            {
                "role": "user",
                "content": (
                    f"Please process the expense statement at: {pdf_path}\n"
                    f"Source file name for tracking: {source_file}"
                ),
            }
        ]

        # ----------------------------------------------------------------
        # Agentic loop — runs until Claude stops calling tools
        # ----------------------------------------------------------------
        final_summary = {}
        max_iterations = 10  # safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=ORCHESTRATOR_SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Collect any text Claude produced (for the final summary)
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    final_summary["message"] = block.text.strip()
                    print(f"[Orchestrator] {block.text.strip()}")

            # If Claude is done, exit the loop
            if response.stop_reason == "end_turn":
                print("\n[Orchestrator] Pipeline complete.")
                break

            # If Claude wants to call tools, execute them
            if response.stop_reason == "tool_use":
                # Append the full assistant response (including tool_use blocks)
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input
                    print(f"\n[Orchestrator] → Calling tool: {tool_name}")

                    try:
                        result = self._execute_tool(tool_name, tool_input, source_file)
                        result_str = json.dumps(result)

                        # Update our running summary
                        if tool_name == "save_transactions" and isinstance(result, dict):
                            final_summary.update(result)

                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})
                        print(f"  [Orchestrator] Tool error: {e}")

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        }
                    )

                # Feed tool results back to Claude
                messages.append({"role": "user", "content": tool_results})

        return final_summary

    # ------------------------------------------------------------------
    # Tool executor — maps tool names to actual agent calls
    # ------------------------------------------------------------------

    def _execute_tool(self, name: str, inputs: dict, source_file: str) -> object:
        """Dispatch a tool call to the appropriate sub-agent."""

        if name == "extract_transactions":
            transactions = self.pdf_extractor.extract(inputs["pdf_path"])
            print(f"  [Orchestrator] ✓ Extracted {len(transactions)} transactions")
            return transactions

        elif name == "categorize_transactions":
            transactions = self.categorizer.categorize(inputs["transactions"])
            print(f"  [Orchestrator] ✓ Categorized {len(transactions)} transactions")
            return transactions

        elif name == "save_transactions":
            sf = inputs.get("source_file", source_file)
            summary = dm.save_transactions(inputs["transactions"], source_file=sf)
            print(
                f"  [Orchestrator] ✓ Saved: {summary['saved']} new, "
                f"{summary['skipped']} duplicates skipped"
            )
            return summary

        else:
            raise ValueError(f"Unknown tool: {name}")
