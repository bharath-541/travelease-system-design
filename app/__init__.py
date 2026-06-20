from flask import Flask

from .db import close_db, init_db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="travelease-academic-demo",
        DATABASE=str(app.instance_path + "/travelease.sqlite3"),
    )

    if test_config:
        app.config.update(test_config)

    app.instance_path_obj = app.instance_path

    from pathlib import Path

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.teardown_appcontext(close_db)

    from .routes import bp

    app.register_blueprint(bp)

    @app.template_filter("currency")
    def currency(value):
        return f"INR {float(value):,.0f}"

    with app.app_context():
        init_db()

    return app
