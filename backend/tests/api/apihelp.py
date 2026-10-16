"""Helpers for API tests: fake demo clock, client wrapper, assertions."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo



IST = ZoneInfo("Asia/Kolkata")
ANCHOR = datetime(2026, 10, 16, 9, 0, tzinfo=IST)


class FakeClock:
    def __init__(self):
        self.now = ANCHOR.astimezone(timezone.utc)

    def advance(self, **kw):
        self.now += timedelta(**kw)


class Api:
    """TestClient wrapper: api.as_("u-staff-f").post(...)."""

    def __init__(self, client, clock, app):
        self.client, self.clock, self.app, self._user = client, clock, app, None

    def as_(self, user):
        a = Api(self.client, self.clock, self.app)
        a._user = user
        return a

    def _h(self, extra=None):
        h = {"X-Demo-User": self._user} if self._user else {}
        h.update(extra or {})
        return h

    def get(self, url, **kw):
        return self.client.get(url, headers=self._h(kw.pop("headers", None)), **kw)

    def post(self, url, json=None, **kw):
        return self.client.post(url, json=json if json is not None else {}, headers=self._h(kw.pop("headers", None)),
                                **kw)

    def session(self):
        return self.app.state.sessionmaker()


def ok(resp, code=200):
    assert resp.status_code == code, resp.text
    return resp.json()


def err(resp, status, code):
    assert resp.status_code == status, resp.text
    assert resp.json()["error"]["code"] == code, resp.text
    return resp.json()["error"]


def run_match(api, policy="strict", **kw):
    return ok(api.as_("u-coord").post("/api/match/run", {"policy": policy, **kw}))


def suggestion(result, frm, to):
    return next(t for t in result["suggested"] if t["from_centre"] == frm and t["to_centre"] == to)
