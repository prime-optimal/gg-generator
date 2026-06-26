import pytest

from gg_generator.identity import address as address_mod
from gg_generator.identity.address import AddressError, generate_address, normalize_state


def _place(city: str, state: str, abbr: str, zip_: str) -> dict:
    """A Zippopotam.us-shaped payload."""
    return {
        "post code": zip_,
        "places": [{"place name": city, "state": state, "state abbreviation": abbr}],
    }


class _Resp:
    def __init__(self, status: int, payload: dict | None = None):
        self.status_code = status
        self._payload = payload

    def json(self) -> dict | None:
        return self._payload

    def raise_for_status(self) -> None:
        pass


class _FakeClient:
    """Returns queued responses in order; the final one repeats once drained."""

    def __init__(self, *responses: _Resp):
        self._responses = list(responses)
        self.calls: list[str] = []

    def get(self, url: str) -> _Resp:
        self.calls.append(url)
        if len(self._responses) > 1:
            return self._responses.pop(0)
        return self._responses[0]


def test_normalize_accepts_abbr_and_name():
    assert normalize_state("ca") == "CA"
    assert normalize_state("California") == "CA"
    assert normalize_state(" texas ") == "TX"


def test_normalize_rejects_unknown():
    with pytest.raises(ValueError):
        normalize_state("Westeros")


def test_generate_address_uses_real_zip_for_state():
    client = _FakeClient(_Resp(200, _place("New York", "New York", "NY", "10001")))
    addr = generate_address("New York", client=client)
    assert addr.state_abbr == "NY"
    assert addr.state == "New York"
    assert addr.city == "New York"  # comes from the resolved real ZIP
    assert addr.zip == "10001"
    assert addr.street and addr.country == "United States"


def test_generate_address_random_when_unspecified(monkeypatch):
    monkeypatch.setattr(address_mod._fake, "state_abbr", lambda **_: "TX")
    client = _FakeClient(_Resp(200, _place("Austin", "Texas", "TX", "73301")))
    addr = generate_address(client=client)
    assert addr.state_abbr == "TX"
    assert addr.zip == "73301"


def test_retries_until_real_zip():
    client = _FakeClient(
        _Resp(404),
        _Resp(404),
        _Resp(200, _place("Buffalo", "New York", "NY", "14201")),
    )
    addr = generate_address("NY", client=client)
    assert addr.zip == "14201"
    assert len(client.calls) == 3


def test_raises_when_no_real_zip():
    client = _FakeClient(_Resp(404))
    with pytest.raises(AddressError):
        generate_address("NY", client=client, attempts=3)
    assert len(client.calls) == 3


def test_skips_zip_resolving_outside_requested_state():
    # A real ZIP, but Zippopotam places it in NJ while we asked for NY -> rejected.
    client = _FakeClient(_Resp(200, _place("Newark", "New Jersey", "NJ", "07101")))
    with pytest.raises(AddressError):
        generate_address("NY", client=client, attempts=2)


def test_one_line_format():
    client = _FakeClient(_Resp(200, _place("Los Angeles", "California", "CA", "90001")))
    addr = generate_address("CA", client=client)
    assert addr.one_line == f"{addr.street}, Los Angeles, CA 90001"
