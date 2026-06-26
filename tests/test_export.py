import csv
import io

from gg_generator.core.export import collect_fieldnames, flatten, profiles_to_csv
from gg_generator.core.models import Address, Identity, Mailbox, Profile


def _profile(gamertag: str = "redpanda123", with_address: bool = True) -> Profile:
    address = (
        Address(street="1 Main St", city="Austin", state="Texas", state_abbr="TX", zip="77001")
        if with_address
        else None
    )
    return Profile(
        gamertag=gamertag,
        password="TONs3kPC",
        identity=Identity(
            gamertag=gamertag,
            first_name="John",
            last_name="Doe",
            gender="male",
            phone="(555) 123-4567",
            dob="1985-03-12",
            age=41,
            address=address,
        ),
        mailbox=Mailbox(email=f"{gamertag}@braindeadfgc.lol", provider="forward"),
        created_at="2026-06-19T00:00:00+00:00",
    )


def test_flatten_uses_dot_notation():
    flat = flatten({"identity": {"address": {"zip": "77001"}}, "gamertag": "x"})
    assert flat == {"identity.address.zip": "77001", "gamertag": "x"}


def test_collect_fieldnames_unions_in_first_seen_order():
    rows = [{"a": 1, "b": 2}, {"b": 2, "c": 3}]
    assert collect_fieldnames(rows) == ["a", "b", "c"]


def test_csv_has_header_and_one_row_per_profile():
    csv_text = profiles_to_csv([_profile("alpha1"), _profile("beta2")])
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(rows) == 2
    assert {r["gamertag"] for r in rows} == {"alpha1", "beta2"}


def test_csv_flattens_nested_identity_and_mailbox():
    csv_text = profiles_to_csv([_profile("alpha1")])
    header = csv_text.splitlines()[0]
    assert "identity.first_name" in header
    assert "identity.address.zip" in header
    assert "mailbox.email" in header
    row = next(csv.DictReader(io.StringIO(csv_text)))
    assert row["identity.address.zip"] == "77001"
    assert row["mailbox.email"] == "alpha1@braindeadfgc.lol"


def test_none_address_renders_empty_cells_and_header_is_union():
    csv_text = profiles_to_csv([_profile("alpha1", with_address=False), _profile("beta2")])
    reader = csv.DictReader(io.StringIO(csv_text))
    assert "identity.address.zip" in reader.fieldnames
    rows = list(reader)
    no_addr = next(r for r in rows if r["gamertag"] == "alpha1")
    assert no_addr["identity.address.zip"] == ""
