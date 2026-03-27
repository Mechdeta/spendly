import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import close_db, get_db, init_db

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-change-this-secret-key"

app.teardown_appcontext(close_db)

with app.app_context():
    init_db()


def parse_month_start(raw_month):
    try:
        return datetime.strptime(raw_month, "%Y-%m").date().replace(day=1)
    except ValueError:
        return None


def next_month_start(month_start):
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def recent_month_options(count=6):
    options = []
    cursor = date.today().replace(day=1)
    for _ in range(count):
        options.append(cursor.strftime("%Y-%m"))
        if cursor.month == 1:
            cursor = date(cursor.year - 1, 12, 1)
        else:
            cursor = date(cursor.year, cursor.month - 1, 1)
    return options


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.")

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        user_id = cursor.lastrowid
        default_categories = ["Food", "Transport", "Bills", "Shopping", "Health", "Other"]
        db.executemany(
            "INSERT INTO categories (user_id, name) VALUES (?, ?)",
            [(user_id, category) for category in default_categories],
        )
        db.commit()
    except sqlite3.IntegrityError:
        return render_template("register.html", error="Email is already registered.")

    session.clear()
    session["user_id"] = user_id
    session["user_name"] = name
    flash("Account created successfully.", "success")
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Email and password are required.")

    db = get_db()
    user = db.execute(
        "SELECT id, name, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    flash("Welcome back.", "success")
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
@login_required
def profile():
    user_id = session["user_id"]
    db = get_db()

    categories = db.execute(
        "SELECT id, name FROM categories WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()

    selected_category = request.args.get("category", type=int)
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    month_param = request.args.get("month", "").strip()

    selected_month_start = parse_month_start(month_param)
    if selected_month_start is None:
        selected_month_start = date.today().replace(day=1)

    selected_month = selected_month_start.strftime("%Y-%m")
    selected_month_end = next_month_start(selected_month_start)

    query = """
        SELECT e.id, e.amount, e.description, e.expense_date, c.name AS category_name
        FROM expenses e
        LEFT JOIN categories c ON c.id = e.category_id
        WHERE e.user_id = ?
    """
    params = [user_id]

    if selected_category:
        query += " AND e.category_id = ?"
        params.append(selected_category)
    if date_from:
        query += " AND e.expense_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND e.expense_date <= ?"
        params.append(date_to)

    query += " ORDER BY e.expense_date DESC, e.id DESC"
    expenses = db.execute(query, tuple(params)).fetchall()
    total_spent = sum(expense["amount"] for expense in expenses)

    monthly_summary = db.execute(
        """
        SELECT
            COALESCE(SUM(amount), 0) AS total,
            COUNT(*) AS count,
            COALESCE(AVG(amount), 0) AS avg
        FROM expenses
        WHERE user_id = ?
          AND expense_date >= ?
          AND expense_date < ?
        """,
        (user_id, selected_month_start.isoformat(), selected_month_end.isoformat()),
    ).fetchone()

    category_breakdown = db.execute(
        """
        SELECT
            COALESCE(c.name, 'Uncategorized') AS category_name,
            SUM(e.amount) AS spent
        FROM expenses e
        LEFT JOIN categories c ON c.id = e.category_id
        WHERE e.user_id = ?
          AND e.expense_date >= ?
          AND e.expense_date < ?
        GROUP BY COALESCE(c.name, 'Uncategorized')
        ORDER BY spent DESC
        """,
        (user_id, selected_month_start.isoformat(), selected_month_end.isoformat()),
    ).fetchall()

    top_category = category_breakdown[0]["category_name"] if category_breakdown else "No data"
    monthly_total = float(monthly_summary["total"] or 0)
    breakdown_rows = []
    for row in category_breakdown:
        spent = float(row["spent"] or 0)
        share = (spent / monthly_total * 100) if monthly_total > 0 else 0
        breakdown_rows.append(
            {
                "category_name": row["category_name"],
                "spent": spent,
                "share": share,
            }
        )

    budget_rows = db.execute(
        """
        SELECT
            b.category_id,
            c.name AS category_name,
            b.amount AS budget_amount,
            COALESCE(SUM(e.amount), 0) AS spent_amount
        FROM budgets b
        JOIN categories c ON c.id = b.category_id
        LEFT JOIN expenses e
            ON e.user_id = b.user_id
           AND e.category_id = b.category_id
           AND e.expense_date >= ?
           AND e.expense_date < ?
        WHERE b.user_id = ?
          AND b.month = ?
        GROUP BY b.category_id, c.name, b.amount
        ORDER BY c.name
        """,
        (
            selected_month_start.isoformat(),
            selected_month_end.isoformat(),
            user_id,
            selected_month,
        ),
    ).fetchall()

    budget_summary = {"budgeted": 0.0, "spent": 0.0}
    budget_progress = []
    for row in budget_rows:
        budget_amount = float(row["budget_amount"] or 0)
        spent_amount = float(row["spent_amount"] or 0)
        percent_used = (spent_amount / budget_amount * 100) if budget_amount > 0 else 0
        budget_summary["budgeted"] += budget_amount
        budget_summary["spent"] += spent_amount
        budget_progress.append(
            {
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "budget_amount": budget_amount,
                "spent_amount": spent_amount,
                "remaining": budget_amount - spent_amount,
                "percent_used": min(percent_used, 100),
                "is_over": spent_amount > budget_amount,
            }
        )

    return render_template(
        "profile.html",
        expenses=expenses,
        categories=categories,
        total_spent=total_spent,
        selected_category=selected_category,
        date_from=date_from,
        date_to=date_to,
        selected_month=selected_month,
        month_options=recent_month_options(),
        monthly_total=monthly_total,
        monthly_count=monthly_summary["count"],
        monthly_avg=float(monthly_summary["avg"] or 0),
        top_category=top_category,
        category_breakdown=breakdown_rows,
        budget_progress=budget_progress,
        budget_summary=budget_summary,
        today=date.today().isoformat(),
    )


@app.route("/budgets/set", methods=["POST"])
@login_required
def set_budget():
    user_id = session["user_id"]
    category_id = request.form.get("category_id", type=int)
    amount_raw = request.form.get("amount", "").strip()
    month_raw = request.form.get("month", "").strip()

    month_start = parse_month_start(month_raw)
    if month_start is None:
        flash("Invalid budget month.", "error")
        return redirect(url_for("profile"))

    try:
        amount = float(amount_raw)
    except ValueError:
        flash("Budget amount must be a valid number.", "error")
        return redirect(url_for("profile", month=month_start.strftime("%Y-%m")))

    if amount <= 0:
        flash("Budget must be greater than zero.", "error")
        return redirect(url_for("profile", month=month_start.strftime("%Y-%m")))

    db = get_db()
    category = db.execute(
        "SELECT id FROM categories WHERE id = ? AND user_id = ?",
        (category_id, user_id),
    ).fetchone()
    if category is None:
        flash("Invalid category selected for budget.", "error")
        return redirect(url_for("profile", month=month_start.strftime("%Y-%m")))

    db.execute(
        """
        INSERT INTO budgets (user_id, category_id, month, amount)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, category_id, month)
        DO UPDATE SET
            amount = excluded.amount,
            updated_at = CURRENT_TIMESTAMP
        """,
        (user_id, category_id, month_start.strftime("%Y-%m"), amount),
    )
    db.commit()
    flash("Budget saved.", "success")
    return redirect(url_for("profile", month=month_start.strftime("%Y-%m")))


@app.route("/expenses/add", methods=["POST"])
@login_required
def add_expense():
    user_id = session["user_id"]
    description = request.form.get("description", "").strip()
    amount_raw = request.form.get("amount", "").strip()
    category_id = request.form.get("category_id", type=int)
    expense_date = request.form.get("expense_date", "").strip() or date.today().isoformat()

    try:
        amount = float(amount_raw)
    except ValueError:
        flash("Amount must be a valid number.", "error")
        return redirect(url_for("profile"))

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")
        return redirect(url_for("profile"))

    db = get_db()
    if category_id:
        category_exists = db.execute(
            "SELECT id FROM categories WHERE id = ? AND user_id = ?",
            (category_id, user_id),
        ).fetchone()
        if category_exists is None:
            flash("Invalid category selected.", "error")
            return redirect(url_for("profile"))

    db.execute(
        """
        INSERT INTO expenses (user_id, category_id, amount, description, expense_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, category_id, amount, description, expense_date),
    )
    db.commit()
    flash("Expense added.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    user_id = session["user_id"]
    db = get_db()

    expense = db.execute(
        """
        SELECT id, amount, description, expense_date, category_id
        FROM expenses
        WHERE id = ? AND user_id = ?
        """,
        (id, user_id),
    ).fetchone()

    if expense is None:
        abort(404)

    categories = db.execute(
        "SELECT id, name FROM categories WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()

    if request.method == "GET":
        return render_template("edit_expense.html", expense=expense, categories=categories)

    description = request.form.get("description", "").strip()
    amount_raw = request.form.get("amount", "").strip()
    category_id = request.form.get("category_id", type=int)
    expense_date = request.form.get("expense_date", "").strip()

    try:
        amount = float(amount_raw)
    except ValueError:
        flash("Amount must be a valid number.", "error")
        return render_template("edit_expense.html", expense=expense, categories=categories)

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")
        return render_template("edit_expense.html", expense=expense, categories=categories)

    if not expense_date:
        flash("Date is required.", "error")
        return render_template("edit_expense.html", expense=expense, categories=categories)

    if category_id:
        category_exists = db.execute(
            "SELECT id FROM categories WHERE id = ? AND user_id = ?",
            (category_id, user_id),
        ).fetchone()
        if category_exists is None:
            flash("Invalid category selected.", "error")
            return render_template("edit_expense.html", expense=expense, categories=categories)

    db.execute(
        """
        UPDATE expenses
        SET amount = ?, description = ?, category_id = ?, expense_date = ?
        WHERE id = ? AND user_id = ?
        """,
        (amount, description, category_id, expense_date, id, user_id),
    )
    db.commit()
    flash("Expense updated.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
@login_required
def delete_expense(id):
    user_id = session["user_id"]
    db = get_db()
    deleted = db.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (id, user_id),
    )
    db.commit()

    if deleted.rowcount == 0:
        flash("Expense not found.", "error")
    else:
        flash("Expense deleted.", "success")

    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
