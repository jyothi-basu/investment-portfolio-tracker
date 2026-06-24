# Software Requirements Specification (SRS)

# Project Title

Investment Portfolio Tracker

# Project Overview

Investment Portfolio Tracker is a web-based application developed as an Agentic AI course assignment. It demonstrates an AI-assisted software development workflow while helping users manage stock investments across multiple demat accounts.

The application allows users to record buy and sell transactions, manually maintain prices for currently held stocks, view holdings, analyze account-wise summaries, and view an overall portfolio summary.

The application is intended for educational purposes and is built using Python, Flask, SQLite, Bootstrap, HTML, CSS, and JavaScript.

---

# Purpose

People may have investments spread across multiple demat accounts. This project helps users track their stock portfolio by recording buy and sell transactions and providing a consolidated portfolio summary.

The project also serves as a course assignment that shows how a structured, AI-assisted development process can be used to produce a complete web application with clear separation of concerns.

---

# Scope

The application shall:

* Allow users to register and log in securely.
* Allow management of multiple demat accounts.
* Allow recording of buy and sell stock transactions.
* Allow users to manually update stock prices only for currently held stocks.
* Allow users to ask questions through an AI chat assistant about the portfolio and the app.
* Display current holdings.
* Display demat account-wise portfolio summaries.
* Display overall portfolio summaries.

The application will not integrate with external stock market APIs.

All stock prices will be maintained manually by users and limited to stocks currently held in the portfolio.

---

# Features

1. User Registration
2. User Login
3. User Logout
4. Add Demat Account
5. Edit Demat Account
6. Delete Demat Account
7. Add Buy Transaction
8. Add Sell Transaction
9. Edit Transaction
10. Delete Transaction
11. Update Stock Prices
12. View Holdings
13. View Demat Account Wise Summary
14. View Portfolio Summary
15. AI Chat Assistant

---

# Application Architecture

The application uses a layered structure:

* `app.py` starts the Flask application.
* `routes.py` handles HTTP requests, form submission, redirects, and flash messages.
* `service.py` contains business rules and portfolio calculations.
* `storage.py` contains SQLite database operations.
* `schema.sql` contains the database schema definition.

This structure is used to keep the code easier to debug, test, and maintain.

---

# Technical Requirements

## Backend

* Python 3
* Flask

## Security

* Bcrypt Password Hashing

## Frontend

* HTML5
* CSS3
* Bootstrap 5
* Vanilla JavaScript

## Database

* SQLite

## Template Engine

* Jinja2

---

# Security Requirements

* Users must register and log in.
* Passwords must be securely hashed using Bcrypt.
* Users must only access their own data.
* Protected pages must require authentication.
* Session-based authentication shall be used.
* Unauthorized users shall be redirected to the login page.

---

# Accessibility Requirements

The application must follow WCAG accessibility principles.

Requirements:

* All form controls must have associated labels.
* All pages must be fully keyboard accessible.
* Use semantic HTML elements.
* Provide meaningful page titles and headings.
* Ensure sufficient color contrast.
* Do not rely solely on color.
* Tables must use proper table headers.
* Buttons and links must have meaningful text.
* Forms must provide accessible validation messages.
* The application should be usable with NVDA.

---

# UI Requirements

* Each feature must be accessible through clearly labeled buttons or navigation links.
* Forms must provide appropriate input fields.
* All user inputs must be validated.
* Validation errors must be displayed clearly.
* Tables should be used to display holdings, transactions, and summaries.
* The interface should be responsive.
* Bootstrap components should be used for consistency.

---

# Functional Requirements

## User Management

Users shall be able to:

* Register
* Login
* Logout

---

## Demat Account Management

Users shall be able to:

* Create demat accounts
* Edit demat accounts
* Delete demat accounts
* View all their demat accounts

Examples:

* Zerodha
* Groww
* Angel One
* ICICI Direct

---

## Transaction Management

Users shall be able to:

* Add buy transactions
* Add sell transactions
* Edit transactions
* Delete transactions

Each transaction shall contain:

* Stock Symbol
* Transaction Type
* Quantity
* Price Per Share
* Transaction Date
* Demat Account

Transaction Types:

* BUY
* SELL

---

## Stock Price Management

Users shall be able to:

* View currently held stocks in a dropdown
* Update stock prices for those currently held stocks
* View the saved price for each held stock

Prices shall be entered manually.
Only stocks currently held across the user's demat accounts shall be available for price updates.

---

## AI Chat Assistant

Users shall be able to:

* Ask questions about their portfolio summary
* Ask questions about holdings and transactions
* Ask questions about how to use the application

The assistant shall use OpenRouter API for text generation.
The assistant shall not access external market data unless such data is explicitly provided by the application.

---

## Holdings Management

The system shall calculate holdings based on transaction history.

Example:

BUY 10 TCS

BUY 5 TCS

SELL 3 TCS

Current Holding = 12 Shares

---

# Portfolio Summary

The dashboard shall display:

* Total Investment Value
* Current Portfolio Value
* Profit or Loss
* Total Stocks Held
* Total Demat Accounts

### Portfolio Calculation Rule

For this project, total investment is calculated as:

* Total Investment = total BUY amount - total SELL amount

Current portfolio value is the market value of the remaining holdings, based on manually entered stock prices for currently held stocks.

Profit or Loss is calculated as:

* Profit or Loss = Current Portfolio Value - Total Investment

---

## Demat Account Wise Summary

The system shall display:

* Broker Name
* Number of Stocks
* Investment Value
* Current Value
* Profit or Loss

for each demat account.

---

# Business Rules

1. Users can only view their own data.
2. A demat account belongs to exactly one user.
3. A user can have multiple demat accounts.
4. A transaction belongs to exactly one demat account.
5. A demat account can have multiple transactions.
6. Transaction type must be BUY or SELL.
7. Quantity must be greater than zero.
8. Price per share must be greater than zero.
9. Users must be authenticated before accessing portfolio data.
10. Portfolio value is calculated using holdings and current stock prices.
11. Total investment is calculated as total BUY amount minus total SELL amount.
12. Foreign key relationships must be enforced to maintain data integrity.

---

# Database Design

## Users

* user_id INTEGER PRIMARY KEY AUTOINCREMENT
* username TEXT NOT NULL
* email TEXT NOT NULL UNIQUE
* password_hash TEXT NOT NULL

## Demat Accounts

* account_id INTEGER PRIMARY KEY AUTOINCREMENT
* user_id INTEGER NOT NULL
* broker_name TEXT NOT NULL

Foreign Key:

* user_id REFERENCES users(user_id)

## Transactions

* transaction_id INTEGER PRIMARY KEY AUTOINCREMENT
* account_id INTEGER NOT NULL
* stock_symbol TEXT NOT NULL
* transaction_type TEXT NOT NULL
* quantity INTEGER NOT NULL
* price_per_share REAL NOT NULL
* transaction_date DATE NOT NULL

Foreign Key:

* account_id REFERENCES demat_accounts(account_id)

## Stock Prices

* price_id INTEGER PRIMARY KEY AUTOINCREMENT
* user_id INTEGER NOT NULL
* stock_symbol TEXT NOT NULL
* current_price REAL NOT NULL
* last_updated DATETIME

Foreign Key:

* user_id REFERENCES users(user_id)

---

# Validation Rules

## Registration

* Username is required.
* Email is required.
* Email must be unique.
* Password is required.
* Password must be at least 8 characters.

## Demat Account

* Broker name is required.

## Transactions

* Stock symbol is required.
* Quantity must be greater than zero.
* Price per share must be greater than zero.
* Transaction type must be BUY or SELL.

## Stock Prices

* At least one current holding must exist before updating stock prices.
* Stock symbol must be one of the user's currently held stocks.
* Current price must be greater than zero.

---

# Pages

1. Home Page
2. Register Page
3. Login Page
4. Dashboard
5. Demat Accounts Page
6. Transactions Page
7. Stock Prices Page
8. Holdings Page
9. Demat Account Wise Summary Page
10. Portfolio Summary Page
11. Chat Page

---

# Suggested Folder Structure

investment_portfolio_tracker/

* app.py
* routes.py
* service.py
* storage.py
* schema.sql
* requirements.txt
* README.md
* SRS.md
* portfolio.db

templates/

* base.html
* home.html
* login.html
* register.html
* dashboard.html
* demat_accounts.html
* transactions.html
* stock_prices.html
* holdings.html
* account_summary.html
* portfolio_summary.html

static/

* style.css
* script.js

---

# Success Criteria

The project shall be considered complete when:

* Users can register and log in.
* Users can manage demat accounts.
* Users can record buy and sell transactions.
* Users can update stock prices only for currently held stocks.
* Users can ask questions through the AI chat assistant.
* Users can view holdings.
* Users can view demat account-wise summaries.
* Users can view portfolio summaries.
* All data is stored in SQLite.
* Foreign key relationships are enforced.
* The application is accessible and usable with NVDA.
