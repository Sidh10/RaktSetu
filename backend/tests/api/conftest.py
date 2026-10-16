from apihelp import ANCHOR, Api, FakeClock  # noqa: F401
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_real_now
from app.config import Settings
from app.db import make_engine
from app.main import create_app
from app.services import seed


@pytest.fixture
def api():
    settings = Settings(database_url="sqlite://")
    app = create_app(settings, make_engine("sqlite://"))
    clock = FakeClock()
    app.dependency_overrides[get_real_now] = lambda: clock.now
    with app.state.sessionmaker() as s:
        seed.load(s, clock.now, settings.tz, ANCHOR)
        s.commit()
    with TestClient(app) as client:
        yield Api(client, clock, app)
