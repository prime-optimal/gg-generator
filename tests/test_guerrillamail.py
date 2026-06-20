import httpx

from gg_generator.mail.guerrillamail import GuerrillaMailClient


def _handler(request):
    f = request.url.params.get("f")
    if f == "get_email_address":
        return httpx.Response(
            200,
            json={
                "email_addr": "abc123@guerrillamailblock.com",
                "sid_token": "tok1",
                "email_timestamp": 123,
                "alias": "abc123",
            },
        )
    if f == "set_email_user":
        # GuerrillaMail must receive the prior sid_token to mutate the session.
        assert request.url.params.get("sid_token") == "tok1"
        return httpx.Response(
            200,
            json={
                "email_addr": "redpanda123@guerrillamailblock.com",
                "sid_token": "tok1",
                "email_timestamp": 123,
                "alias": "redpanda123",
            },
        )
    if f == "check_email":
        return httpx.Response(
            200,
            json={
                "list": [
                    {
                        "mail_id": "1",
                        "mail_from": "noreply@service.test",
                        "mail_subject": "Verify your account",
                        "mail_date": "2026-06-19 12:00:00",
                    }
                ],
                "sid_token": "tok1",
            },
        )
    return httpx.Response(200, json={})


def _client() -> GuerrillaMailClient:
    http = httpx.Client(transport=httpx.MockTransport(_handler))
    return GuerrillaMailClient(client=http)


def test_provision_and_bind_flow():
    gm = _client()
    gm.get_address()
    assert gm.sid_token == "tok1"

    mailbox = gm.set_user("redpanda123")
    assert mailbox.email == "redpanda123@guerrillamailblock.com"
    assert mailbox.sid_token == "tok1"


def test_check_inbox():
    gm = _client()
    gm.get_address()
    messages = gm.check_inbox()
    assert messages[0]["mail_subject"] == "Verify your account"


def test_resume_with_saved_token():
    gm = GuerrillaMailClient(
        sid_token="tok1", client=httpx.Client(transport=httpx.MockTransport(_handler))
    )
    # No get_address() call — the saved token alone must drive check_email.
    assert gm.check_inbox()[0]["mail_id"] == "1"
