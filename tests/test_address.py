import pytest

from gg_generator.identity.address import generate_address, normalize_state


def test_normalize_accepts_abbr_and_name():
    assert normalize_state("ca") == "CA"
    assert normalize_state("California") == "CA"
    assert normalize_state(" texas ") == "TX"


def test_normalize_rejects_unknown():
    with pytest.raises(ValueError):
        normalize_state("Westeros")


def test_generate_address_pins_state():
    addr = generate_address("New York")
    assert addr.state_abbr == "NY"
    assert addr.state == "New York"
    assert addr.country == "United States"
    assert addr.zip and addr.street and addr.city


def test_generate_address_random_when_unspecified():
    addr = generate_address()
    assert len(addr.state_abbr) == 2
    assert addr.zip


def test_one_line_format():
    addr = generate_address("CA")
    assert addr.one_line == f"{addr.street}, {addr.city}, CA {addr.zip}"
