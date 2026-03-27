# Spendly

A clean and modern personal expense tracker built with Flask and SQLite.

Spendly helps users:
- register and manage their own account
- track expenses with categories and dates
- edit and delete transactions safely
- monitor monthly analytics
- set category-wise budgets and track progress
- switch between light and night mode

## Highlights

- Authentication with hashed passwords
- Session-based protected dashboard
- Full expense CRUD for each user
- Monthly analytics:
  - total spend
  - transaction count
  - average transaction value
  - top spending category
  - category-wise breakdown
- Budget tracking by category and month
- Responsive UI with theme persistence
- SQLite with foreign keys, constraints, and indexes

## Tech Stack

- Backend: Flask 3.1
- Database: SQLite
- Frontend: Jinja templates, vanilla CSS, vanilla JavaScript
- Testing deps: pytest, pytest-flask

## Project Structure

```text
spendly/
├── app.py
├── requirements.txt
├── expense_tracker.db
├── database/
│   ├── __init__.py
│   └── db.py
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── templates/
    ├── base.html
    ├── landing.html
    ├── login.html
    ├── register.html
    ├── profile.html
    └── edit_expense.html
```

## Quick Start

### 1) Clone and open

```bash
git clone https://github.com/Mechdeta/spendly.git
cd spendly
```

### 2) Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Run app

```bash
python3 app.py
```

App runs at:
- http://127.0.0.1:5001

## How It Works

### App startup flow

1. Flask app is created in app.py.
2. Database connection lifecycle hooks are registered.
3. init_db() runs on startup and creates tables if they do not exist.
4. Each request gets one SQLite connection (via Flask g).
5. Connection is closed automatically at request end.

### User flow

1. User registers with name, email, and password.
2. Password is hashed using Werkzeug.
3. Default categories are created for the user.
4. User is logged in with session values.
5. Protected pages (dashboard and write routes) require login.

### Expense flow

- Add: validates amount/category and inserts row
- Edit: checks ownership and updates row
- Delete: checks ownership and removes row

### Budget flow

- Budget is set per user + category + month
- Uses UPSERT behavior (insert or update existing)
- Dashboard joins budgets with expenses to show progress and over-budget state

## Database Design

Database file:
- expense_tracker.db

Managed in:
- database/db.py

### Tables

#### users

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT |
| name | TEXT | NOT NULL |
| email | TEXT | NOT NULL, UNIQUE |
| password_hash | TEXT | NOT NULL |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP |

#### categories

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT |
| user_id | INTEGER | FK -> users(id), ON DELETE CASCADE |
| name | TEXT | NOT NULL |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP |

Constraint:
- UNIQUE(user_id, name)

#### expenses

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT |
| user_id | INTEGER | FK -> users(id), ON DELETE CASCADE |
| category_id | INTEGER | FK -> categories(id), ON DELETE SET NULL |
| amount | REAL | NOT NULL, CHECK(amount > 0) |
| description | TEXT | optional |
| expense_date | TEXT | NOT NULL (YYYY-MM-DD) |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP |

#### budgets

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT |
| user_id | INTEGER | FK -> users(id), ON DELETE CASCADE |
| category_id | INTEGER | FK -> categories(id), ON DELETE CASCADE |
| month | TEXT | NOT NULL (YYYY-MM) |
| amount | REAL | NOT NULL, CHECK(amount > 0) |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TEXT | DEFAULT CURRENT_TIMESTAMP |

Constraint:
- UNIQUE(user_id, category_id, month)

### Indexes

- idx_expenses_user_date on (user_id, expense_date)
- idx_expenses_user_category on (user_id, category_id)
- idx_budgets_user_month on (user_id, month)

## Route Reference

### Public

- GET / -> landing page (redirects to dashboard when already logged in)
- GET/POST /register -> create account
- GET/POST /login -> sign in

### Protected

- GET /logout -> sign out
- GET /profile -> dashboard + filters + analytics + budget status
- POST /budgets/set -> add/update monthly category budget
- POST /expenses/add -> add expense
- GET/POST /expenses/<id>/edit -> edit expense
- POST /expenses/<id>/delete -> delete expense

## UI and Theme

Spendly ships with both light and night mode.

- Toggle available in the top navigation
- Preference is stored in localStorage
- Theme is applied early on page load to avoid flashing wrong theme

## Security Notes

Current protections:
- Password hashing with Werkzeug
- Session-based route protection
- User ownership checks for edit/delete/write operations
- SQL parameter binding used throughout queries

Suggested next upgrades:
- Move SECRET_KEY to environment variable
- Add CSRF protection
- Add login rate limiting
- Add secure cookie settings for production

## Testing

Dependencies are included for pytest and pytest-flask.

Run tests:

```bash
pytest -q
```

## Roadmap

- Export expenses to CSV
- Recurring expenses
- Search and pagination for large data sets
- Better analytics visualizations
- API endpoints for mobile integration

## Contributing

1. Fork this repository
2. Create a feature branch
3. Commit with clear messages
4. Open a pull request

## License

No license file is currently defined in this repository.
If you plan to open-source widely, add a LICENSE file (for example MIT).
