import base64

import pytest

from app.core.config import Settings
from app.core.sensitive_data import (
    SensitiveDataIntegrityError,
    build_sensitive_data_cipher,
)


def build_cipher():
    return build_sensitive_data_cipher(
        Settings(
            _env_file=None,
            patient_data_keys={"v1": base64.b64encode(b"a" * 32).decode()},
            patient_data_active_key_id="v1",
            patient_lookup_key=base64.b64encode(b"b" * 32).decode(),
        )
    )


def test_sensitive_text_and_json_round_trip() -> None:
    cipher = build_cipher()
    text = cipher.encrypt_text("Klinik not", purpose="case_details.special_notes")
    payload = cipher.encrypt_json({"renk": "şeffaf"}, purpose="case_details.extra_fields")

    assert b"Klinik not" not in text
    assert cipher.decrypt_text(text, purpose="case_details.special_notes") == "Klinik not"
    assert cipher.decrypt_json(payload, purpose="case_details.extra_fields") == {"renk": "şeffaf"}


def test_sensitive_cipher_binds_ciphertext_to_purpose() -> None:
    cipher = build_cipher()
    encrypted = cipher.encrypt_text("Gizli", purpose="audit_events.reason")

    with pytest.raises(SensitiveDataIntegrityError):
        cipher.decrypt_text(encrypted, purpose="case_approvals.reason")
