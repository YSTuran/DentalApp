import string

import pytest

from app.services.firebase_identity import generate_temporary_password


def test_temporary_password_meets_minimum_complexity() -> None:
    password = generate_temporary_password()

    assert len(password) == 20
    assert any(character in string.ascii_uppercase for character in password)
    assert any(character in string.ascii_lowercase for character in password)
    assert any(character in string.digits for character in password)
    assert any(character in "!@#$%*-_" for character in password)


def test_temporary_password_rejects_short_length() -> None:
    with pytest.raises(ValueError):
        generate_temporary_password(15)
