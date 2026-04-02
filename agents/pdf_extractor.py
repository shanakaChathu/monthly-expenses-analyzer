"""
PDF Extractor Agent
-------------------
Reads a credit card PDF statement and returns a list of raw transactions.

Pipeline:
  1. pdfplumber extracts raw text from every page of the PDF.
  2. That text is sent to Claude (claude-opus-4-6) with a focused system
     prompt that instructs it to return only a JSON array of transactions.
  3. The JSON is parsed and returned as a Python list of dicts.

Why use Claude here instead of regex?
  Credit card statements vary greatly in layout. Claude can handle different
  date formats, column orders, and irregular spacing far more reliably than
  hand-crafted rules.
"""

import json
import os

import pdfplumber
import anthropic
from dotenv import load_dotenv

from prompts.system_prompts import PDF_EXTRACTOR_SYSTEM_PROMPT

load_dotenv()


class PDFExtractorAgent:
    """Extracts structured transactions from a PDF bank statement."""

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-opus-4-6"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def extract(self, pdf_path: str) -> list[dict]:
        """
        Main entry point.

        Args:
            pdf_path: Absolute or relative path to the PDF file.

        Returns:
            List of transaction dicts with keys:
              date, description, amount, currency, transaction_type
        """
        print(f"  [PDFExtractor] Reading PDF: {pdf_path}")
        raw_text = self._read_pdf(pdf_path)

        if not raw_text.strip():
            raise ValueError(f"Could not extract any text from {pdf_path}")

        print(f"  [PDFExtractor] Extracted {len(raw_text)} characters from PDF")
        print("  [PDFExtractor] Sending to Claude for transaction parsing...")

        transactions = self._parse_with_claude(raw_text)
        print(f"  [PDFExtractor] Found {len(transactions)} transactions")
        return transactions

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_pdf(self, pdf_path: str) -> str:
        """Use pdfplumber to extract all text from every page."""
        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Try extracting tables first (better for tabular statements)
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if row:
                                pages_text.append(
                                    " | ".join(str(cell) if cell else "" for cell in row)
                                )
                else:
                    # Fall back to plain text extraction
                    text = page.extract_text()
                    if text:
                        pages_text.append(f"--- Page {i + 1} ---\n{text}")

        return "\n".join(pages_text)

    def _parse_with_claude(self, raw_text: str) -> list[dict]:
        """
        Send extracted PDF text to Claude and get back structured transactions.

        Uses adaptive thinking so Claude can reason about ambiguous layouts.
        """
        # Truncate if extremely long to stay within context limits
        max_chars = 180_000
        if len(raw_text) > max_chars:
            raw_text = raw_text[:max_chars] + "\n[... truncated ...]"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            thinking={"type": "adaptive"},
            system=PDF_EXTRACTOR_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Here is the raw text extracted from a credit card PDF statement. "
                        "Please extract all transactions and return them as a JSON array.\n\n"
                        f"{raw_text}"
                    ),
                }
            ],
        )

        # Find the text block in the response (skip thinking blocks)
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text = block.text
                break

        return self._parse_json_response(response_text)

    def _parse_json_response(self, text: str) -> list[dict]:
        """
        Parse Claude's response as a JSON array.
        Handles cases where Claude wraps the JSON in markdown code fences.
        """
        text = text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            # Try to find a JSON array within the text
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                try:
                    data = json.loads(text[start:end])
                except json.JSONDecodeError:
                    raise ValueError(
                        f"Could not parse JSON from Claude's response: {e}\n"
                        f"Response preview: {text[:500]}"
                    )
            else:
                raise ValueError(
                    f"No JSON array found in Claude's response: {e}\n"
                    f"Response preview: {text[:500]}"
                )

        if not isinstance(data, list):
            raise ValueError(f"Expected a JSON array, got {type(data)}")

        # Basic validation and normalisation
        cleaned = []
        for tx in data:
            if not isinstance(tx, dict):
                continue
            if not tx.get("description") or tx.get("amount") is None:
                continue
            cleaned.append({
                "date": str(tx.get("date", "")),
                "description": str(tx.get("description", "")).strip(),
                "amount": abs(float(tx.get("amount", 0))),
                "currency": str(tx.get("currency", "AED")),
                "transaction_type": str(tx.get("transaction_type", "debit")).lower(),
            })

        return cleaned
