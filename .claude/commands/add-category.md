# Add a New Expense Category

This command helps you add a new expense category to `config/categories.json`.

## Steps

1. Read the current categories file to see what already exists:
   ```
   config/categories.json
   ```

2. Ask the user for:
   - **Category name** (e.g. "Pet Care")
   - **Colour** (hex code, e.g. `#FF6B6B`) — pick something distinct from existing ones
   - **Keywords** — merchant names or words that signal this category
     (e.g. `["petco", "vet", "veterinary", "pet shop", "animal clinic"]`)

3. Add the new entry to the `"categories"` array in `config/categories.json`:
   ```json
   {
     "name": "Pet Care",
     "color": "#F4A261",
     "icon": "🐾",
     "keywords": ["petco", "vet", "veterinary", "pet shop", "animal clinic"]
   }
   ```

4. Confirm the file was saved and remind the user:
   > The Categorizer Agent will use these keywords as hints the next time you
   > process a statement. Already-saved transactions are not re-categorized
   > automatically — re-run `python main.py --pdf <file>` to reprocess.

## Tips
- Keywords are case-insensitive hints for Claude — they guide it but Claude
  also reasons about context, so a few good keywords are enough.
- Choose a colour that contrasts with existing ones so the dashboard charts
  are easy to read.
- Use an emoji icon that represents the category visually.