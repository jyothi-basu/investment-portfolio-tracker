import os

from dotenv import load_dotenv
from flask import Flask

import storage
from routes import register_routes

load_dotenv()


def create_app():
    app = Flask(__name__)
    register_routes(app)
    return app


app = create_app()
storage.init_db()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )