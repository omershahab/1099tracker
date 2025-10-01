# 1099 Expense Tracker — v2.3 (UI refresh + monthly toggle)

- Monthly chart toggle between *Spent* and *Deductible* (Meals @50%).
- Friendlier UI: cleaner layout, spacing, and a sticky **Quick Add** bar.
- Faster Add Expense: today's date prefilled; tax year auto; amount accepts `$`/commas;
  last category remembered; vendor→category autosuggest; "Save & Add Another".
- Deployment-ready (Gunicorn + `$PORT`).

## Quick start
1. Import the zip to Replit.
2. Set Secrets: `SECRET_KEY`, `APP_USER`, `APP_PASS`.
3. `pip install -r requirements.txt`
4. **Run** (dev) or **Deploy** with `gunicorn -w 2 -b 0.0.0.0:$PORT main:app`
