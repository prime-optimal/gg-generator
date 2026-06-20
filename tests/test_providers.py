import pytest

from gg_generator.core.models import Mailbox
from gg_generator.mail.providers import (
    DEFAULT_FORWARD_DOMAIN,
    ForwardProvider,
    GuerrillaProvider,
    MailProviderError,
    get_provider,
    provider_for,
)


def test_forward_provision_mints_catchall_address():
    mb = ForwardProvider().provision("redpanda123")
    assert mb.email == f"redpanda123@{DEFAULT_FORWARD_DOMAIN}"
    assert mb.provider == "forward"
    assert mb.sid_token == ""


def test_forward_custom_domain():
    mb = ForwardProvider(domain="example.test").provision("foo")
    assert mb.email == "foo@example.test"


def test_forward_has_no_inbox():
    fp = ForwardProvider()
    assert fp.supports_inbox is False
    mb = fp.provision("foo")
    with pytest.raises(MailProviderError):
        fp.check_inbox(mb)
    with pytest.raises(MailProviderError):
        fp.fetch(mb, "1")


def test_get_provider_factory():
    assert isinstance(get_provider("guerrilla"), GuerrillaProvider)
    assert isinstance(get_provider("forward", "x.test"), ForwardProvider)
    with pytest.raises(MailProviderError):
        get_provider("smoke-signals")


def test_provider_for_reconstructs_from_mailbox():
    fwd = provider_for(Mailbox(email="a@x.test", provider="forward"))
    assert isinstance(fwd, ForwardProvider)
    assert fwd.domain == "x.test"

    gm = provider_for(Mailbox(email="a@guerrillamail.com", provider="guerrilla", sid_token="t"))
    assert isinstance(gm, GuerrillaProvider)
