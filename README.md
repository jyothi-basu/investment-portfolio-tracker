# Investment Portfolio Tracker

Investment Portfolio Tracker is a Flask-based web application developed as an Agentic AI course assignment. The project demonstrates an AI-assisted software development workflow while providing a practical tool for tracking stock investments across multiple demat accounts.

The application lets a user record buy and sell transactions, manually maintain prices for currently held stocks, and view holdings and portfolio summaries in one place.

This project is intended for educational use and course evaluation.

## Course Context

This application was created for an Agentic AI assignment. The goal is to show how an AI-assisted development process can be used to plan, structure, build, and document a functional software system.

## What This App Does

The application helps you:

- create an account and log in securely
- manage multiple demat accounts
- record `BUY` and `SELL` stock transactions
- manually update stock prices for stocks currently held in the portfolio
- view current holdings
- view demat account-wise summaries
- view an overall portfolio summary
- use an AI chat assistant for portfolio and app-related questions

The app does not connect to any external stock market API. All stock prices are entered by the user.

## For Users

If you want to use the application as a normal user, here is the flow:

1. Open the application in your browser.
2. Create a new account using the `Register` page.
3. Log in with your email and password.
4. Add one or more demat accounts such as Zerodha, Groww, Angel One, or ICICI Direct.
5. Add your stock transactions.
6. Update the current stock prices for stocks you currently hold.
7. Open the dashboard to see your holdings and portfolio summary.

### Main Pages

- `Home` - landing page with login and register links
- `Register` - create a new user account
- `Login` - sign in to your account
- `Dashboard` - see total investment, current portfolio value, profit or loss, and holdings
- `Demat Accounts` - add, edit, or delete broker accounts
- `Transactions` - add, edit, or delete buy and sell transactions
- `Stock Prices` - update prices for currently held stocks
- `Holdings` - view current stock holdings
- `Demat Account Wise Summary` - see summary for each demat account
- `Portfolio Summary` - see overall portfolio details
- `Chat` - ask the AI assistant about your portfolio and the app

### How Portfolio Values Are Calculated

The application uses a simple rule set:

- `Total Investment = total BUY amount - total SELL amount`
- `Current Portfolio Value = current value of remaining holdings`
- `Profit/Loss = Current Portfolio Value - Total Investment`

Example:

- You buy shares worth `100`
- Later you sell shares worth `80`
- Your total investment becomes `20`
- If the remaining holdings are worth `120`, your profit is `100`

### Important Notes for Users

- You must log in before using portfolio pages.
- You can only see your own data.
- Stock prices must be entered manually and only for stocks currently held in the portfolio.
- The AI chat assistant requires `OPENROUTER_API_KEY` to be set in the environment.
- If you delete a demat account, its transactions are also removed.
- If you enter invalid values, the app will show a validation message.

## For Setup / Maintenance

This section is for anyone who wants to run the project locally, test it, or continue maintenance. The person using this section might be a developer, a tester, a maintainer, or a technically comfortable user.

### Tech Stack

- Python 3
- Flask
- SQLite
- Jinja2
- Bootstrap 5
- Vanilla JavaScript
- bcrypt for password hashing

### Project Structure

```text
investment_portfolio_tracker/
├── app.py
├── routes.py
├── service.py
├── storage.py
├── schema.sql
├── requirements.txt
├── README.md
├── SRS.md
├── portfolio.db
├── static/
│   ├── style.css
│   └── script.js
└── templates/
    ├── base.html
    ├── home.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── demat_accounts.html
    ├── transactions.html
    ├── stock_prices.html
    ├── holdings.html
    ├── account_summary.html
    └── portfolio_summary.html
```

### Setup Instructions

1. Make sure Python 3 is installed.
2. Open a terminal in the project folder.
3. Install the dependencies:

```bash
pip install -r requirements.txt
```

4. Run the application:

```bash
python app.py
```

5. Open the browser at the local address shown in the terminal, usually:

```text
http://127.0.0.1:5000
```

### Architecture

The project is organized in layers:

- `routes.py` handles HTTP requests, form handling, and redirects
- `service.py` handles business rules
- `storage.py` handles SQLite operations
- `schema.sql` defines the database schema
- `app.py` starts the Flask application

### Design Goal

The codebase is intentionally split into clear layers so it is easier to debug, test, and extend:

- request handling stays in `routes.py`
- business decisions stay in `service.py`
- database access stays in `storage.py`
- the schema stays in `schema.sql`

### Database

The app uses SQLite and creates a local database file named `portfolio.db`.

The main tables are:

- `users`
- `demat_accounts`
- `transactions`
- `stock_prices`

### Authentication

User passwords are stored securely using bcrypt hashing. Session-based authentication is used, and protected pages require login.

### Validation Rules

The app currently validates:

- username is required
- email is required and must be unique
- password must be at least 8 characters
- broker name is required
- stock symbol is required
- transaction type must be `BUY` or `SELL`
- quantity must be greater than zero
- price per share must be greater than zero
- current stock price must be greater than zero

### Accessibility Notes

The UI follows basic accessibility practices:

- labels are associated with form controls
- pages use semantic structure
- tables are used for tabular data
- the interface is keyboard-friendly
- Bootstrap is used for responsive layout support

## Troubleshooting

### The app does not start

- Confirm that Python is installed
- Install dependencies again with `pip install -r requirements.txt`
- Check for errors in the terminal

### Registration fails

- Make sure the email is not already used
- Make sure the password is at least 8 characters long

### Portfolio numbers look wrong

- Check that transactions were entered correctly
- Confirm that stock prices are updated only for currently held stocks
- Make sure `BUY` and `SELL` quantities are valid

### Chat does not respond

- Confirm that `OPENROUTER_API_KEY` is set
- Check that the selected OpenRouter model is valid
- Verify your internet connection

## License

This project is intended for learning and educational use and is licensed under the [MIT License](LICENSE).
