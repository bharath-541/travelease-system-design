import pytest

from app import create_app
from app.db import init_db
from app.services import SearchService


@pytest.fixture()
def app(tmp_path):
    database = tmp_path / "test.sqlite3"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(database),
            "SECRET_KEY": "test-key",
        }
    )
    with app.app_context():
        init_db(reset=True)
        SearchService._cache.clear()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()
