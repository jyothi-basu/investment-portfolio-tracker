CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS demat_accounts (
    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    broker_name TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    stock_symbol TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price_per_share REAL NOT NULL,
    transaction_date TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES demat_accounts(account_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stock_prices (
    price_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_symbol TEXT NOT NULL,
    current_price REAL NOT NULL,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, stock_symbol),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
