from bcrypt import checkpw, gensalt, hashpw

import storage


def fetch_user(user_id):
    if user_id is None:
        return None
    return storage.fetch_user_by_id(user_id)


def register_user(username, email, password):
    if storage.email_exists(email):
        return False, "That email is already registered."

    password_hash = hashpw(password.encode("utf-8"), gensalt()).decode("utf-8")
    storage.create_user(username, email, password_hash)
    return True, "Registration successful. Please log in."


def authenticate_user(email, password):
    user = storage.fetch_user_by_email(email)
    if not user:
        return None
    if checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return user
    return None


def fetch_accounts(user_id):
    return storage.fetch_accounts(user_id)


def fetch_account(account_id, user_id):
    return storage.fetch_account(account_id, user_id)


def create_account(user_id, broker_name):
    if not broker_name:
        return False, "Broker name is required."
    storage.create_account(user_id, broker_name)
    return True, "Demat account added."


def update_account(account_id, user_id, broker_name):
    if not broker_name:
        return False, "Broker name is required."
    if not storage.fetch_account(account_id, user_id):
        return False, "Account not found."
    storage.update_account(account_id, broker_name)
    return True, "Demat account updated."


def delete_account(account_id, user_id):
    if not storage.fetch_account(account_id, user_id):
        return False, "Account not found."
    storage.delete_account(account_id)
    return True, "Demat account deleted."


def fetch_transactions(user_id):
    return storage.fetch_transactions(user_id)


def fetch_transaction(transaction_id, user_id):
    return storage.fetch_transaction(transaction_id, user_id)


def _account_stock_quantity(account_id, symbol, exclude_transaction_id=None):
    return storage.fetch_account_stock_quantity(account_id, symbol, exclude_transaction_id=exclude_transaction_id)


def create_transaction(user_id, account_id, stock_symbol, transaction_type, quantity, price_per_share, transaction_date):
    if not storage.fetch_account(account_id, user_id):
        return False, "Please select a valid demat account."
    if not stock_symbol:
        return False, "Stock symbol is required."
    if transaction_type not in {"BUY", "SELL"}:
        return False, "Transaction type must be BUY or SELL."
    if quantity <= 0:
        return False, "Quantity must be greater than zero."
    if price_per_share <= 0:
        return False, "Price per share must be greater than zero."
    if not transaction_date:
        return False, "Transaction date is required."

    current_qty = _account_stock_quantity(account_id, stock_symbol)
    if transaction_type == "SELL" and current_qty < quantity:
        return False, "You cannot sell more shares than you currently hold in this account."

    storage.create_transaction(account_id, stock_symbol, transaction_type, quantity, price_per_share, transaction_date)
    return True, "Transaction added."


def update_transaction(user_id, transaction_id, account_id, stock_symbol, transaction_type, quantity, price_per_share, transaction_date):
    if not storage.fetch_transaction(transaction_id, user_id):
        return False, "Transaction not found."
    if not storage.fetch_account(account_id, user_id):
        return False, "Please select a valid demat account."
    if not stock_symbol:
        return False, "Stock symbol is required."
    if transaction_type not in {"BUY", "SELL"}:
        return False, "Transaction type must be BUY or SELL."
    if quantity <= 0:
        return False, "Quantity must be greater than zero."
    if price_per_share <= 0:
        return False, "Price per share must be greater than zero."
    if not transaction_date:
        return False, "Transaction date is required."

    current_qty = _account_stock_quantity(account_id, stock_symbol, exclude_transaction_id=transaction_id)
    if transaction_type == "SELL" and current_qty < quantity:
        return False, "You cannot sell more shares than you currently hold in this account."

    storage.update_transaction(
        transaction_id,
        account_id,
        stock_symbol,
        transaction_type,
        quantity,
        price_per_share,
        transaction_date,
    )
    return True, "Transaction updated."


def delete_transaction(transaction_id, user_id):
    if not storage.fetch_transaction(transaction_id, user_id):
        return False, "Transaction not found."
    storage.delete_transaction(transaction_id)
    return True, "Transaction deleted."


def fetch_prices(user_id):
    return storage.fetch_prices(user_id)


def fetch_current_holding_symbols(user_id):
    return {row["stock_symbol"].upper() for row in storage.fetch_holding_rows_by_symbol(user_id)}


def save_price(user_id, stock_symbol, current_price):
    normalized_symbol = stock_symbol.strip().upper() if stock_symbol else ""
    if not normalized_symbol:
        return False, "Stock symbol is required."
    if current_price <= 0:
        return False, "Current price must be greater than zero."
    if normalized_symbol not in fetch_current_holding_symbols(user_id):
        return False, "You can only update prices for stocks you currently hold."

    storage.save_price(user_id, normalized_symbol, current_price)
    return True, "Stock price saved."


def calculate_holdings_by_symbol(user_id):
    rows = storage.fetch_holding_rows_by_symbol(user_id)
    holdings = []
    for row in rows:
        qty = int(row["quantity"])
        current_price = float(row["current_price"] or 0)
        holdings.append(
            {
                "stock_symbol": row["stock_symbol"],
                "quantity": qty,
                "current_price": current_price,
                "current_value": qty * current_price,
            }
        )
    return holdings


def calculate_holdings_by_account(user_id):
    rows = storage.fetch_holding_rows_by_account(user_id)
    accounts = {}
    for row in rows:
        account_id = row["account_id"]
        accounts.setdefault(
            account_id,
            {
                "account_id": account_id,
                "broker_name": row["broker_name"],
                "symbols": [],
                "investment_value": 0.0,
                "current_value": 0.0,
            },
        )
        qty = int(row["quantity"])
        current_price = float(row["current_price"] or 0)
        investment_value = float(row["investment_value"] or 0)
        current_value = qty * current_price
        accounts[account_id]["symbols"].append(
            {
                "stock_symbol": row["stock_symbol"],
                "quantity": qty,
                "current_price": current_price,
                "current_value": current_value,
            }
        )
        accounts[account_id]["investment_value"] += investment_value
        accounts[account_id]["current_value"] += current_value
    return list(accounts.values())


def calculate_portfolio_summary(user_id):
    total_investment_row = storage.fetch_total_investment_row(user_id)
    holdings = calculate_holdings_by_symbol(user_id)
    total_current_value = sum(item["current_value"] for item in holdings)
    total_investment = float(total_investment_row["total_investment"] or 0)
    return {
        "total_investment": total_investment,
        "current_portfolio_value": total_current_value,
        "profit_loss": total_current_value - total_investment,
        "total_stocks_held": len(holdings),
        "total_demat_accounts": storage.fetch_account_count(user_id),
    }
