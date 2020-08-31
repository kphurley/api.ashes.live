"""Standard pytest fixtures used across all API tests

## USAGE
    from fastapi import status
    from fastapi.testclient import TestClient

    def test_endpoint(client: TestClient):
        response = client.get("/my-endpoint/")
        assert response.status == status.HTTP_200_OK
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy_utils import create_database, drop_database, database_exists

# `models` is necessary to ensure that AlchemyBase is properly populated
from api import app, db, settings, models


@pytest.fixture(scope="session")
def session_local():
    """Override the default database with our testing database, and make sure to run migrations"""
    test_engine = create_engine(
        (
            f"postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/test"
        ),
        echo=False,
    )
    # Drop database and recreate to ensure tests are always run against a clean slate
    if database_exists(test_engine.url):
        drop_database(test_engine.url)
    create_database(test_engine.url)
    TestSessionLocal = sessionmaker(bind=test_engine)
    # Create all tables
    db.AlchemyBase.metadata.create_all(bind=test_engine)
    try:
        yield TestSessionLocal
    finally:
        drop_database(test_engine.url)
        pass


@pytest.fixture(scope="function")
def client(session_local: Session) -> TestClient:
    """Return a FastAPI TestClient for issuing requests and rollback session transaction"""
    session = session_local()
    session.begin_nested()

    def override_get_session():
        yield session

    app.dependency_overrides[db.get_session] = override_get_session

    try:
        yield TestClient(app)
    finally:
        session.rollback()
        session.close()