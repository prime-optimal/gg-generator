import pytest

from gg_generator.passwords import MIN_LENGTH, generate_password


def test_default_satisfies_policy():
    for _ in range(200):
        pw = generate_password()
        assert len(pw) == MIN_LENGTH
        assert any(c.isdigit() for c in pw), pw
        assert any(c.isupper() for c in pw), pw


def test_custom_length():
    pw = generate_password(16)
    assert len(pw) == 16
    assert any(c.isdigit() for c in pw)
    assert any(c.isupper() for c in pw)


def test_too_short_rejected():
    with pytest.raises(ValueError):
        generate_password(MIN_LENGTH - 1)


def test_randomized():
    assert generate_password() != generate_password()
