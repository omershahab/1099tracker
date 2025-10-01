# 1099 Expense Tracker (Flask + SQLite) — v2

Adds:
- Simple login (username/password via environment variables)
- CSV import
- Chart.js dashboard

## Quick start on Replit

1. Import this zip into a new Python Repl.
2. In the Replit **Secrets** (Environment variables), set:
   - `SECRET_KEY` = any long random string
   - `APP_USER`   = your login username (e.g., `omer`)
   - `APP_PASS`   = your login password (e.g., `strongpass123`)
3. Open the Shell and run: `pip install -r requirements.txt`
4. Click **Run**. Login at `/login`.

## CSV Import
Go to **Expenses → Import CSV**. Supported headers (case-insensitive):
- `date` (YYYY-MM-DD), `description`, `vendor`, `amount`, `category`, `payment_method`,
  `tax_year`, `project`, `location`, `receipt_url`, `miles`, `mileage_rate`, `is_deductible`, `notes`

Any missing optional fields default to sensible values. `is_deductible`: 1/0 or true/false/yes/no.

## Charts
Visit **Dashboard** and **Charts** for Category and Monthly views.

> Not tax, accounting, or legal advice.
