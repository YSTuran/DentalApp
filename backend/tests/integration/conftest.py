from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.db.session import engine, get_db
from app.main import app


@pytest.fixture
def case_session_factory() -> Generator[sessionmaker[Session]]:
    with engine.connect() as connection:
        outer_transaction = connection.begin()
        factory = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        def override_get_db():
            with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            yield factory
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            outer_transaction.rollback()
