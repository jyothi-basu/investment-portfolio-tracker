import os

from dotenv import load_dotenv

from app import create_app
from app.repository.db import init_db


load_dotenv()


app = create_app()
init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
