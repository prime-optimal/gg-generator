import httpx
import pytest

from gg_generator.identity.zippopotam import ZippopotamError, lookup_zip


class _Resp:
    def __init__(self, status: int, payload: dict | None = None):
        self.status_code = status
        self._payload = payload

    def json(self) -> dict | None:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)


class _Client:
    def __init__(self, resp: _Resp | Exception):
        self._resp = resp

    def get(self, url: str):
        if isinstance(self._resp, Exception):
            raise self._resp
        return self._resp


_PAYLOAD = {
    "post code": "90210",
    "places": [
        {"place name": "Beverly Hills", "state": "California", "state abbreviation": "CA"}
    ],
}


def test_lookup_parses_real_zip():
    result = lookup_zip("90210", client=_Client(_Resp(200, _PAYLOAD)))
    assert result == {
        "city": "Beverly Hills",
        "state": "California",
        "state_abbr": "CA",
        "zip": "90210",
    }


def test_lookup_returns_none_on_404():
    assert lookup_zip("00000", client=_Client(_Resp(404))) is None


def test_lookup_raises_on_network_error():
    with pytest.raises(ZippopotamError, match="request failed"):
        lookup_zip("90210", client=_Client(httpx.ConnectError("boom")))


def test_lookup_raises_on_unexpected_shape():
    with pytest.raises(ZippopotamError, match="unexpected"):
        lookup_zip("90210", client=_Client(_Resp(200, {"post code": "90210"})))
