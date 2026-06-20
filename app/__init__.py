import os
from pathlib import Path

from flask import Flask

from .db import close_db, get_db, init_db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    default_database = str(Path(app.instance_path) / "travelease.sqlite3")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get(
            "SECRET_KEY", "travelease-academic-demo"
        ),
        DATABASE=os.environ.get("DATABASE_PATH", default_database),
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.teardown_appcontext(close_db)

    from .routes import bp

    app.register_blueprint(bp)

    @app.template_filter("currency")
    def currency(value):
        return f"INR {float(value):,.0f}"

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return {"status": "ok"}

    with app.app_context():
        init_db()

    return app
