import subprocess

import pytest

from gg_generator.core.models import Address, Identity, Mailbox, Profile
from gg_generator.vault.onepassword import (
    DEVELOPER_VAULT,
    OnePasswordError,
    build_create_args,
    create_login,
)


def _profile() -> Profile:
    return Profile(
        gamertag="redpanda123",
        password="TONs3kPC",
        identity=Identity(
            gamertag="redpanda123",
            first_name="John",
            last_name="Doe",
            gender="male",
            phone="(555) 123-4567",
            dob="1985-03-12",
            age=41,
            address=Address(
                street="1 Main St",
                city="Austin",
                state="Texas",
                state_abbr="TX",
                zip="77001",
            ),
        ),
        mailbox=Mailbox(email="redpanda123@braindeadfgc.lol", provider="forward"),
        created_at="2026-06-19T00:00:00+00:00",
    )


def test_build_args_has_core_fields():
    args = build_create_args(_profile())
    assert args[:3] == ["op", "item", "create"]
    assert "--category=login" in args
    assert f"--vault={DEVELOPER_VAULT}" in args
    assert "--title=redpanda123" in args
    assert "username=redpanda123" in args
    assert "password=TONs3kPC" in args
    assert "email[text]=redpanda123@braindeadfgc.lol" in args
    assert "address[text]=1 Main St, Austin, TX 77001" in args


def test_no_sid_field_for_forward_backend():
    args = build_create_args(_profile())
    assert not any(a.startswith("guerrilla_sid_token") for a in args)


def test_sid_field_present_for_guerrilla():
    prof = _profile()
    prof.mailbox = Mailbox(email="x@guerrillamail.com", provider="guerrilla", sid_token="tok1")
    args = build_create_args(prof)
    assert "guerrilla_sid_token[password]=tok1" in args


def test_dry_run_returns_command_without_executing():
    result = create_login(_profile(), dry_run=True)
    assert result["dry_run"] is True
    assert result["command"][:3] == ["op", "item", "create"]


def test_create_login_parses_op_json():
    def fake_runner(args, capture_output, text):
        return subprocess.CompletedProcess(args, 0, stdout='{"id": "abc123"}', stderr="")

    result = create_login(_profile(), runner=fake_runner)
    assert result["id"] == "abc123"


def test_create_login_raises_on_failure():
    def fake_runner(args, capture_output, text):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="not signed in")

    with pytest.raises(OnePasswordError, match="not signed in"):
        create_login(_profile(), runner=fake_runner)
