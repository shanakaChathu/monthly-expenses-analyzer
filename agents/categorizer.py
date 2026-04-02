"""
Categorizer Agent
-----------------
Takes a list of raw transactions and assigns each one a category and
subcategory using Claude.

Why Claude instead of keyword matching?
  Merchant names on bank statements are often truncated or coded
  (e.g. "TALBOUT 00123 DUBAI"). Simple keyword matching fails here.
  Claude understands the context and can infer the category even from
  noisy or abbreviated merchant names.
"""

import json
import os

import anthropic
from dotenv import load_dotenv

from prompts.system_prompts import CATEGORIZER_SYSTEM_PROMPT

load_dotenv()

CATEGORIES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "categories.json"
)

# Process in batches to avoid token limits
BATCH_SIZE = 50


class CategorizerAgent:
    """Assigns expense categories to transactions using Claude."""

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-opus-4-6"
        self.categories = self._load_categories()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def categorize(self, transactions: list[dict]) -> list[dict]:
        """
        Main entry point.

        Args:
            transactions: List of transaction dicts from PDFExtractorAgent.

        Returns:
            Same list with 'category' and 'subcategory' fields added.
        """
        if not transactions:
            return []

        print(f"  [Categorizer] Categorizing {len(transactions)} transactions...")

        # Process in batches so we don't exceed token limits
        results = []
        for i in range(0, len(transactions), BATCH_SIZE):
            batch = transactions[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(transactions) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"  [Categorizer] Batch {batch_num}/{total_batches} ({len(batch)} transactions)...")
            categorized = self._categorize_batch(batch)
            results.extend(categorized)

        print(f"  [Categorizer] Done. {len(results)} transactions categorized.")
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_categories(self) -> list[dict]:
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("categories", [])

    def _build_categories_list(self) -> str:
        """Build a human-readable list of categories for the prompt."""
        lines = []
        for cat in self.categories:
            keywords_preview = ", ".join(cat.get("keywords", [])[:5])
            if len(cat.get("keywords", [])) > 5:
                keywords_preview += ", ..."
            lines.append(f"- {cat['name']} (hints: {keywords_preview})")
        return "\n".join(lines)

    def _categorize_batch(self, transactions: list[dict]) -> list[dict]:
        """Send a batch to Claude for categorization."""
        categories_list = self._build_categories_list()
        system_prompt = CATEGORIZER_SYSTEM_PROMPT.format(
            categories_list=categories_list
        )

        user_message = (
            "Please categorize the following transactions. "
            "Return the same JSON array with 'category' and 'subcategory' added.\n\n"
            f"{json.dumps(transactions, indent=2)}"
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text = block.text
                break

        return self._parse_json_response(response_text, fallback=transactions)

    def _parse_json_response(
        self, text: str, fallback: list[dict]
    ) -> list[dict]:
        """
        Parse Claude's JSON response. On failure, return the original
        transactions with 'Others' as the category.
        """
        text = text.strip()

        # Strip markdown fences
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                try:
                    data = json.loads(text[start:end])
                except json.JSONDecodeError:
                    data = None
            else:
                data = None

        if not isinstance(data, list):
            # Fallback: return transactions with default category
            print("  [Categorizer] Warning: Could not parse response, using 'Others'")
            return [
                {**tx, "category": "Others", "subcategory": "Uncategorized"}
                for tx in fallback
            ]

        # Merge categorization results back, ensuring all required fields exist
        result = []
        for tx in data:
            if not isinstance(tx, dict):
                continue
            result.append({
                "date": tx.get("date", ""),
                "description": tx.get("description", ""),
                "amount": float(tx.get("amount", 0)),
                "currency": tx.get("currency", "AED"),
                "transaction_type": tx.get("transaction_type", "debit"),
                "category": tx.get("category", "Others"),
                "subcategory": tx.get("subcategory", ""),
            })

        return result
