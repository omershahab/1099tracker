import os, csv, sqlite3, datetime, io
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, jsonify, session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "expenses.db")
STATIC_DIR = os.path.join(APP_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "receipts")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {"png", "jpg", "jpeg", "pdf"}

CATEGORIES = [
    "CME/Conferences", "Books/Journals", "Licensing/DEA/Board Fees",
    "Malpractice", "Scrubs/Laundry", "Equipment & Devices",
    "Home Office", "Phone/Internet", "Medical Software/Subscriptions",
    "Travel - Air/Hotel", "Meals (50%)", "Parking/Tolls",
    "Car - Fuel/Maint", "Mileage (auto)", "Health Insurance (SEHI)",
    "Office Supplies", "Legal/Accounting", "Marketing/Website",
    "Retirement Contributions (employer)", "Other"
]

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dt TEXT NOT NULL,
        description TEXT,
        vendor TEXT,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        payment_method TEXT,
        tax_year INTEGER NOT NULL,
        project TEXT,
        location TEXT,
        receipt_path TEXT,
        miles REAL DEFAULT 0,
        mileage_rate REAL DEFAULT 0.67,
        is_deductible INTEGER DEFAULT 1,
        notes TEXT,
        created_at TEXT
    )
    """)
    con.commit()
    con.close()

init_db()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

APP_USER = os.environ.get("APP_USER", "admin")
APP_PASS = os.environ.get("APP_PASS", "password")

# ------------------------------
# Auth helpers
# ------------------------------
def logged_in():
    return session.get("auth") == True

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username","")
        p = request.form.get("password","")
        if u == APP_USER and p == APP_PASS:
            session["auth"] = True
            flash("Logged in.")
            nxt = request.args.get("next") or url_for("home")
            return redirect(nxt)
        flash("Invalid credentials.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("login"))

# ------------------------------
# Utility helpers
# ------------------------------
def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def parse_date(s):
    try:
        return datetime.date.fromisoformat(s)
    except Exception:
        return datetime.date.today()

def parse_bool(val, default=1):
    if val is None: return default
    s = str(val).strip().lower()
    if s in ("1","true","yes","y"): return 1
    if s in ("0","false","no","n"): return 0
    try:
        return 1 if float(s) != 0 else 0
    except: return default

# ------------------------------
# Routes
# ------------------------------
@app.route("/")
@login_required
def home():
    today = datetime.date.today()
    y = int(request.args.get("year", today.year))
    con = get_db()
    rows = con.execute(
        "SELECT category, SUM(amount + (miles*mileage_rate)) as total "
        "FROM expenses WHERE tax_year=? AND is_deductible=1 GROUP BY category ORDER BY total DESC", (y,)
    ).fetchall()
    total = con.execute(
        "SELECT SUM(amount + (miles*mileage_rate)) as total FROM expenses WHERE tax_year=? AND is_deductible=1", (y,)
    ).fetchone()["total"]
    con.close()
    return render_template("report.html", rows=rows, total=total or 0.0, year=y, categories=CATEGORIES)

@app.route("/charts")
@login_required
def charts():
    return render_template("charts.html")

@app.route("/expenses")
@login_required
def list_expenses():
    q = []
    params = []

    year = request.args.get("year")
    month = request.args.get("month")
    cat = request.args.get("category")
    text = request.args.get("q")

    if year:
        q.append("tax_year=?"); params.append(int(year))
    if month:
        q.append("strftime('%m', dt)=?"); params.append(f"{int(month):02d}")
    if cat and cat != "All":
        q.append("category=?"); params.append(cat)
    if text:
        q.append("(description LIKE ? OR vendor LIKE ? OR notes LIKE ?)")
        like = f"%{text}%"
        params.extend([like, like, like])

    where = (" WHERE " + " AND ".join(q)) if q else ""
    sql = ("SELECT id, dt, description, vendor, amount, category, payment_method, tax_year, "
           "project, location, receipt_path, miles, mileage_rate, is_deductible, notes "
           "FROM expenses" + where + " ORDER BY dt DESC, id DESC")

    con = get_db()
    rows = con.execute(sql, params).fetchall()
    con.close()
    return render_template("expenses.html", rows=rows, categories=CATEGORIES)

@app.route("/add", methods=["POST"])
@login_required
def add():
    form = request.form
    dt = parse_date(form.get("dt")).isoformat()
    desc = form.get("description") or ""
    vendor = form.get("vendor") or ""
    amount = float(form.get("amount") or 0)
    category = form.get("category") or "Other"
    payment = form.get("payment_method") or ""
    tax_year = int(form.get("tax_year") or dt[:4])
    project = form.get("project") or ""
    location = form.get("location") or ""
    notes = form.get("notes") or ""
    is_deductible = 1 if form.get("is_deductible", "on") == "on" else 0
    miles = float(form.get("miles") or 0)
    mileage_rate = float(form.get("mileage_rate") or 0.67)

    receipt_path = ""
    file = request.files.get("receipt")
    if file and file.filename and allowed(file.filename):
        from datetime import datetime as dtmod
        fname = f"{dtmod.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
        save_path = os.path.join(UPLOAD_DIR, fname)
        file.save(save_path)
        receipt_path = f"/static/receipts/{fname}"

    con = get_db()
    con.execute("""
        INSERT INTO expenses (dt, description, vendor, amount, category, payment_method, tax_year,
                              project, location, receipt_path, miles, mileage_rate, is_deductible,
                              notes, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (dt, desc, vendor, amount, category, payment, tax_year, project, location, receipt_path,
          miles, mileage_rate, is_deductible, notes, datetime.datetime.utcnow().isoformat()))
    con.commit()
    con.close()
    flash("Expense added.")
    return redirect(url_for("list_expenses"))

@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    con = get_db()
    con.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    con.commit()
    con.close()
    flash("Deleted.")
    return redirect(request.referrer or url_for("list_expenses"))

# ------------------------------
# CSV Export / Import
# ------------------------------
@app.route("/export.csv")
@login_required
def export_csv():
    q, params = [], []
    year = request.args.get("year")
    month = request.args.get("month")
    cat = request.args.get("category")
    text = request.args.get("q")
    if year: q.append("tax_year=?"); params.append(int(year))
    if month: q.append("strftime('%m', dt)=?"); params.append(f"{int(month):02d}")
    if cat and cat != "All": q.append("category=?"); params.append(cat)
    if text:
        like = f"%{text}%"
        q.append("(description LIKE ? OR vendor LIKE ? OR notes LIKE ?)")
        params.extend([like, like, like])
    where = (" WHERE " + " AND ".join(q)) if q else ""
    sql = ("SELECT dt, description, vendor, amount, category, payment_method, tax_year, project, "
           "location, receipt_path, miles, mileage_rate, is_deductible, notes FROM expenses" +
           where + " ORDER BY dt ASC")

    con = get_db()
    rows = con.execute(sql, params).fetchall()

    tmp_path = os.path.join(APP_DIR, "export.csv")
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date","description","vendor","amount","category","payment_method","tax_year",
                         "project","location","receipt_url","miles","mileage_rate","is_deductible","notes"])
        for r in rows:
            writer.writerow([r["dt"], r["description"], r["vendor"], r["amount"], r["category"],
                             r["payment_method"], r["tax_year"], r["project"], r["location"],
                             r["receipt_path"], r["miles"], r["mileage_rate"], r["is_deductible"], r["notes"]])
    con.close()
    return send_file(tmp_path, as_attachment=True, download_name="expenses_export.csv")

@app.route("/import", methods=["GET","POST"])
@login_required
def import_csv():
    if request.method == "POST":
        file = request.files.get("csv")
        if not file or not file.filename.lower().endswith(".csv"):
            flash("Please upload a CSV file.")
            return redirect(url_for("import_csv"))
        data = file.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(data))
        inserted = 0
        con = get_db()
        for row in reader:
            # Normalize keys
            norm = { (k or '').strip().lower(): (v or '').strip() for k,v in row.items() }
            dt = norm.get("date") or datetime.date.today().isoformat()
            try:
                dt = datetime.date.fromisoformat(dt).isoformat()
            except:
                # try common mm/dd/yyyy
                try:
                    m,d,y = dt.split("/")
                    dt = datetime.date(int(y), int(m), int(d)).isoformat()
                except:
                    dt = datetime.date.today().isoformat()
            desc = norm.get("description", "")
            vendor = norm.get("vendor", "")
            amount = float(norm.get("amount", "0") or 0)
            category = norm.get("category", "Other") or "Other"
            payment = norm.get("payment_method", "")
            tax_year = int(norm.get("tax_year", dt[:4]) or dt[:4])
            project = norm.get("project", "")
            location = norm.get("location", "")
            receipt_path = norm.get("receipt_url", "")
            miles = float(norm.get("miles", "0") or 0)
            mileage_rate = float(norm.get("mileage_rate", "0.67") or 0.67)
            is_deductible = parse_bool(norm.get("is_deductible"), default=1)
            notes = norm.get("notes", "")

            con.execute("""
                INSERT INTO expenses (dt, description, vendor, amount, category, payment_method, tax_year,
                                      project, location, receipt_path, miles, mileage_rate, is_deductible,
                                      notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (dt, desc, vendor, amount, category, payment, tax_year, project, location, receipt_path,
                    miles, mileage_rate, is_deductible, notes, datetime.datetime.utcnow().isoformat()))
            inserted += 1
        con.commit()
        con.close()
        flash(f"Imported {inserted} rows.")
        return redirect(url_for("list_expenses"))
    return render_template("import.html")


# ------------------------------
# APIs for charts
# ------------------------------
@app.route("/api/totals")
@login_required
def api_totals():
    year = int(request.args.get("year", datetime.date.today().year))
    con = get_db()
    rows = con.execute("SELECT category, SUM(amount + (miles*mileage_rate)) as total "
                       "FROM expenses WHERE tax_year=? GROUP BY category", (year,)).fetchall()
    grand = con.execute("SELECT SUM(amount + (miles*mileage_rate)) as total "
                        "FROM expenses WHERE tax_year=?", (year,)).fetchone()["total"]
    con.close()
    return jsonify({
        "year": year,
        "grand_total": round(grand or 0.0, 2),
        "by_category": {r["category"]: round(r["total"] or 0.0, 2) for r in rows}
    })

@app.route("/api/monthly")
@login_required
def api_monthly():
    year = int(request.args.get("year", datetime.date.today().year))
    con = get_db()
    rows = con.execute("""
        SELECT strftime('%m', dt) AS m, SUM(amount + (miles*mileage_rate)) AS total
        FROM expenses
        WHERE tax_year=?
        GROUP BY m
        ORDER BY m
    """, (year,)).fetchall()
    con.close()
    months = ["01","02","03","04","05","06","07","08","09","10","11","12"]
    series = [0.0]*12
    for r in rows:
        idx = int(r["m"]) - 1
        series[idx] = round(r["total"] or 0.0, 2)
    return jsonify({"year": year, "series": series})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
