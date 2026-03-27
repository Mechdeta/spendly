import sqlite3
from pathlib import Path

from flask import g
from werkzeug.security import generate_password_hash


DATABASE_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"


def get_db():
    if "db" not in g:
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
	db = get_db()

	db.execute(
		"""
		CREATE TABLE IF NOT EXISTS users (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			email TEXT NOT NULL UNIQUE,
			password_hash TEXT NOT NULL,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		)
		"""
	)

	db.execute(
		"""
		CREATE TABLE IF NOT EXISTS categories (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			user_id INTEGER NOT NULL,
			name TEXT NOT NULL,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			UNIQUE(user_id, name),
			FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
		)
		"""
	)

	db.execute(
		"""
		CREATE TABLE IF NOT EXISTS expenses (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			user_id INTEGER NOT NULL,
			category_id INTEGER,
			amount REAL NOT NULL CHECK(amount > 0),
			description TEXT,
			expense_date TEXT NOT NULL,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
			FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
		)
		"""
	)

	db.execute(
		"""
		CREATE TABLE IF NOT EXISTS budgets (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			user_id INTEGER NOT NULL,
			category_id INTEGER NOT NULL,
			month TEXT NOT NULL,
			amount REAL NOT NULL CHECK(amount > 0),
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			UNIQUE(user_id, category_id, month),
			FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
			FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
		)
		"""
	)

	db.execute(
		"CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, expense_date)"
	)
	db.execute(
		"CREATE INDEX IF NOT EXISTS idx_expenses_user_category ON expenses(user_id, category_id)"
	)
	db.execute(
		"CREATE INDEX IF NOT EXISTS idx_budgets_user_month ON budgets(user_id, month)"
	)

	db.commit()


def seed_db():
	db = get_db()
	existing = db.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.local",)).fetchone()
	if existing is not None:
		return

	cursor = db.execute(
		"INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
		("Demo User", "demo@spendly.local", generate_password_hash("password123")),
	)
	user_id = cursor.lastrowid

	categories = ["Food", "Transport", "Bills", "Shopping", "Health", "Other"]
	db.executemany(
		"INSERT INTO categories (user_id, name) VALUES (?, ?)",
		[(user_id, category) for category in categories],
	)

	category_rows = db.execute(
		"SELECT id, name FROM categories WHERE user_id = ?",
		(user_id,),
	).fetchall()
	category_map = {row["name"]: row["id"] for row in category_rows}

	db.executemany(
		"""
		INSERT INTO expenses (user_id, category_id, amount, description, expense_date)
		VALUES (?, ?, ?, ?, ?)
		""",
		[
			(user_id, category_map["Food"], 450.0, "Groceries", "2026-03-10"),
			(user_id, category_map["Transport"], 120.0, "Metro card top-up", "2026-03-12"),
			(user_id, category_map["Bills"], 1500.0, "Electricity bill", "2026-03-15"),
		],
	)

	db.execute(
		"""
		INSERT INTO budgets (user_id, category_id, month, amount)
		VALUES (?, ?, ?, ?), (?, ?, ?, ?)
		""",
		(
			user_id,
			category_map["Food"],
			"2026-03",
			2000.0,
			user_id,
			category_map["Transport"],
			"2026-03",
			1000.0,
		),
	)
	db.commit()
