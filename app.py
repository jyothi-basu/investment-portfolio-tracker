from flask import Flask

import storage
from routes import register_routes


def create_app():
    app = Flask(__name__)
    register_routes(app)
    return app


app = create_app()
storage.init_db()


if __name__ == "__main__":
    app.run(debug=True)
