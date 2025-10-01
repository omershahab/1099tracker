# 1099 Expense Tracker — v2.2 (Meals 50% deductible view)

- Deployment-ready (Gunicorn + `$PORT`).
- Simple login via env (APP_USER/APP_PASS).
- CSV import + charts.
- NEW: Dashboard shows **Spent** vs **Estimated Deductible** (Meals auto-halved).
- `/api/totals?mode=deductible` returns category totals with Meals at 50%.

## Replit quick start
1. Import this zip.
2. Secrets: `SECRET_KEY`, `APP_USER`, `APP_PASS`.
3. `pip install -r requirements.txt`
4. **Run** for dev; **Deployments** uses: `gunicorn -w 2 -b 0.0.0.0:$PORT main:app`
