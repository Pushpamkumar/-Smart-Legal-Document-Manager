import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def client():
    db_path = Path("test_smart_legal_manager.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    from app.main import create_app
    from app.database import Base, engine

    app = create_app()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if db_path.exists():
        db_path.unlink()
    os.environ.pop("DATABASE_URL", None)
