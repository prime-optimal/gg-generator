import httpx
import pytest

from gg_generator.identity.randomuser import RandomUserError, fetch_person

SAMPLE = {
    "results": [
        {
            "gender": "male",
            "name": {"first": "John", "last": "Doe"},
            "login": {"username": "redpanda123"},
            "phone": "(555) 123-4567",
            "nat": "US",
            "picture": {"large": "https://example.test/large.jpg"},
        }
    ]
}


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_person_maps_fields():
    person = fetch_person(client=_client(lambda req: httpx.Response(200, json=SAMPLE)))
    assert person["username"] == "redpanda123"
    assert person["first_name"] == "John"
    assert person["phone"] == "(555) 123-4567"
    assert person["picture"] == "https://example.test/large.jpg"


def test_defaults_to_us_and_passes_gender():
    seen = {}

    def handler(request):
        seen.update(dict(request.url.params))
        return httpx.Response(200, json=SAMPLE)

    fetch_person(gender="female", client=_client(handler))
    assert seen["nat"] == "us"
    assert seen["gender"] == "female"


def test_http_error_wrapped():
    with pytest.raises(RandomUserError):
        fetch_person(client=_client(lambda req: httpx.Response(503)))


def test_bad_shape_wrapped():
    with pytest.raises(RandomUserError):
        fetch_person(client=_client(lambda req: httpx.Response(200, json={"results": []})))
