from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "portfolio.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def query(sql, params=(), one=False):
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        if one:
            return rows[0] if rows else None
        return rows
    finally:
        conn.close()


def execute(sql, params=()):
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def fetch_user_by_id(user_id):
    return query(
        "SELECT user_id, username, email FROM users WHERE user_id = ?",
        (user_id,),
        one=True,
    )


def fetch_user_by_email(email):
    return query(
        "SELECT * FROM users WHERE email = ?",
        (email,),
        one=True,
    )


def email_exists(email):
    return query("SELECT 1 FROM users WHERE email = ?", (email,), one=True) is not None


def create_user(username, email, password_hash):
    return execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, password_hash),
    )


def fetch_accounts(user_id):
    return query(
        "SELECT * FROM demat_accounts WHERE user_id = ? ORDER BY broker_name",
        (user_id,),
    )


def fetch_account(account_id, user_id):
    return query(
        "SELECT * FROM demat_accounts WHERE account_id = ? AND user_id = ?",
        (account_id, user_id),
        one=True,
    )


def create_account(user_id, broker_name):
    return execute(
        "INSERT INTO demat_accounts (user_id, broker_name) VALUES (?, ?)",
        (user_id, broker_name),
    )


def update_account(account_id, broker_name):
    return execute(
        "UPDATE demat_accounts SET broker_name = ? WHERE account_id = ?",
        (broker_name, account_id),
    )


def delete_account(account_id):
    return execute("DELETE FROM demat_accounts WHERE account_id = ?", (account_id,))


def fetch_transactions(user_id):
    return query(
        """
        SELECT t.*, a.broker_name
        FROM transactions t
        JOIN demat_accounts a ON a.account_id = t.account_id
        WHERE a.user_id = ?
        ORDER BY t.transaction_date DESC, t.transaction_id DESC
        """,
        (user_id,),
    )


def fetch_transaction(transaction_id, user_id):
    return query(
        """
        SELECT t.*
        FROM transactions t
        JOIN demat_accounts a ON a.account_id = t.account_id
        WHERE t.transaction_id = ? AND a.user_id = ?
        """,
        (transaction_id, user_id),
        one=True,
    )


def create_transaction(account_id, stock_symbol, transaction_type, quantity, price_per_share, transaction_date):
    return execute(
        """
        INSERT INTO transactions
        (account_id, stock_symbol, transaction_type, quantity, price_per_share, transaction_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (account_id, stock_symbol, transaction_type, quantity, price_per_share, transaction_date),
    )


def update_transaction(transaction_id, account_id, stock_symbol, transaction_type, quantity, price_per_share, transaction_date):
    return execute(
        """
        UPDATE transactions
        SET account_id = ?, stock_symbol = ?, transaction_type = ?, quantity = ?, price_per_share = ?, transaction_date = ?
        WHERE transaction_id = ?
        """,
        (account_id, stock_symbol, transaction_type, quantity, price_per_share, transaction_date, transaction_id),
    )


def delete_transaction(transaction_id):
    return execute("DELETE FROM transactions WHERE transaction_id = ?", (transaction_id,))


def fetch_account_stock_quantity(account_id, symbol, exclude_transaction_id=None):
    params = [account_id, symbol]
    exclude_clause = ""
    if exclude_transaction_id is not None:
        exclude_clause = "AND t.transaction_id != ?"
        params.append(exclude_transaction_id)
    row = query(
        f"""
        SELECT COALESCE(SUM(
            CASE
                WHEN t.transaction_type = 'BUY' THEN t.quantity
                ELSE -t.quantity
            END
        ), 0) AS qty
        FROM transactions t
        WHERE t.account_id = ? AND UPPER(t.stock_symbol) = UPPER(?) {exclude_clause}
        """,
        params,
        one=True,
    )
    return int(row["qty"] if row else 0)


def fetch_prices(user_id):
    return query(
        "SELECT * FROM stock_prices WHERE user_id = ? ORDER BY stock_symbol",
        (user_id,),
    )


def save_price(user_id, stock_symbol, current_price):
    return execute(
        """
        INSERT INTO stock_prices (user_id, stock_symbol, current_price, last_updated)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, stock_symbol)
        DO UPDATE SET current_price = excluded.current_price, last_updated = CURRENT_TIMESTAMP
        """,
        (user_id, stock_symbol, current_price),
    )


def fetch_holding_rows_by_symbol(user_id):
    return query(
        """
        SELECT
            UPPER(t.stock_symbol) AS stock_symbol,
            SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.quantity ELSE -t.quantity END) AS quantity,
            MAX(COALESCE(sp.current_price, 0)) AS current_price
        FROM transactions t
        JOIN demat_accounts a ON a.account_id = t.account_id
        LEFT JOIN stock_prices sp
            ON sp.user_id = a.user_id AND UPPER(sp.stock_symbol) = UPPER(t.stock_symbol)
        WHERE a.user_id = ?
        GROUP BY UPPER(t.stock_symbol)
        HAVING quantity > 0
        ORDER BY stock_symbol
        """,
        (user_id,),
    )


def fetch_holding_rows_by_account(user_id):
    return query(
        """
        SELECT
            a.account_id,
            a.broker_name,
            UPPER(t.stock_symbol) AS stock_symbol,
            SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.quantity ELSE -t.quantity END) AS quantity,
            MAX(COALESCE(sp.current_price, 0)) AS current_price,
            SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.quantity * t.price_per_share ELSE -t.quantity * t.price_per_share END) AS investment_value
        FROM transactions t
        JOIN demat_accounts a ON a.account_id = t.account_id
        LEFT JOIN stock_prices sp
            ON sp.user_id = a.user_id AND UPPER(sp.stock_symbol) = UPPER(t.stock_symbol)
        WHERE a.user_id = ?
        GROUP BY a.account_id, a.broker_name, UPPER(t.stock_symbol)
        ORDER BY a.broker_name, stock_symbol
        """,
        (user_id,),
    )


def fetch_total_investment_row(user_id):
    return query(
        """
        SELECT COALESCE(SUM(
            CASE
                WHEN t.transaction_type = 'BUY' THEN t.quantity * t.price_per_share
                ELSE -t.quantity * t.price_per_share
            END
        ), 0) AS total_investment
        FROM transactions t
        JOIN demat_accounts a ON a.account_id = t.account_id
        WHERE a.user_id = ?
        """,
        (user_id,),
        one=True,
    )


def fetch_account_count(user_id):
    row = query(
        "SELECT COUNT(*) AS total FROM demat_accounts WHERE user_id = ?",
        (user_id,),
        one=True,
    )
    return int(row["total"] if row else 0)
