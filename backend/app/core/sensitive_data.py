import base64
import json
import os
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings, get_settings

ENVELOPE_PREFIX = b"DS1"
NONCE_BYTES = 12


class SensitiveDataConfigurationError(RuntimeError):
    pass


class SensitiveDataIntegrityError(RuntimeError):
    pass


def _decode_key(value: str, *, setting_name: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise SensitiveDataConfigurationError(
            f"{setting_name} geçerli Base64 biçiminde olmalıdır."
        ) from error
    if len(decoded) != 32:
        raise SensitiveDataConfigurationError(f"{setting_name} tam olarak 32 bayt olmalıdır.")
    return decoded


class SensitiveDataCipher:
    def __init__(self, *, keys: Mapping[str, bytes], active_key_id: str) -> None:
        if active_key_id not in keys:
            raise SensitiveDataConfigurationError("Etkin hassas veri anahtarı bulunamadı.")
        if any(len(key) != 32 for key in keys.values()):
            raise SensitiveDataConfigurationError("Hassas veri anahtarları 32 bayt olmalıdır.")
        try:
            valid_ids = all(0 < len(key_id.encode("ascii")) <= 32 for key_id in keys)
        except UnicodeEncodeError as error:
            raise SensitiveDataConfigurationError(
                "Anahtar kimlikleri yalnızca ASCII karakter içermelidir."
            ) from error
        if not valid_ids:
            raise SensitiveDataConfigurationError(
                "Anahtar kimlikleri 1-32 ASCII karakter olmalıdır."
            )
        self._keys = dict(keys)
        self._active_key_id = active_key_id

    def encrypt_bytes(self, value: bytes, *, purpose: str) -> bytes:
        self._validate_purpose(purpose)
        key_id = self._active_key_id.encode("ascii")
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = AESGCM(self._keys[self._active_key_id]).encrypt(
            nonce,
            value,
            self._associated_data(purpose),
        )
        return ENVELOPE_PREFIX + bytes([len(key_id)]) + key_id + nonce + ciphertext

    def decrypt_bytes(self, envelope: bytes, *, purpose: str) -> bytes:
        self._validate_purpose(purpose)
        try:
            if not envelope.startswith(ENVELOPE_PREFIX):
                raise ValueError
            key_id_length = envelope[len(ENVELOPE_PREFIX)]
            key_id_start = len(ENVELOPE_PREFIX) + 1
            nonce_start = key_id_start + key_id_length
            ciphertext_start = nonce_start + NONCE_BYTES
            if key_id_length == 0 or len(envelope) <= ciphertext_start:
                raise ValueError
            key_id = envelope[key_id_start:nonce_start].decode("ascii")
            return AESGCM(self._keys[key_id]).decrypt(
                envelope[nonce_start:ciphertext_start],
                envelope[ciphertext_start:],
                self._associated_data(purpose),
            )
        except (IndexError, InvalidTag, KeyError, UnicodeDecodeError, ValueError) as error:
            raise SensitiveDataIntegrityError(
                "Hassas veri çözülemedi veya bütünlük kontrolü başarısız oldu."
            ) from error

    def encrypt_text(self, value: str, *, purpose: str) -> bytes:
        return self.encrypt_bytes(value.encode("utf-8"), purpose=purpose)

    def decrypt_text(self, envelope: bytes, *, purpose: str) -> str:
        try:
            return self.decrypt_bytes(envelope, purpose=purpose).decode("utf-8")
        except UnicodeDecodeError as error:
            raise SensitiveDataIntegrityError("Şifreli metin UTF-8 biçiminde değil.") from error

    def encrypt_json(self, value: Any, *, purpose: str) -> bytes:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return self.encrypt_bytes(encoded, purpose=purpose)

    def decrypt_json(self, envelope: bytes, *, purpose: str) -> Any:
        try:
            return json.loads(self.decrypt_bytes(envelope, purpose=purpose))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise SensitiveDataIntegrityError("Şifreli JSON verisi geçersiz.") from error

    @staticmethod
    def _validate_purpose(purpose: str) -> None:
        try:
            encoded = purpose.encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError("Hassas veri amacı ASCII olmalıdır.") from error
        if not encoded or len(encoded) > 100:
            raise ValueError("Hassas veri amacı 1-100 karakter olmalıdır.")

    @staticmethod
    def _associated_data(purpose: str) -> bytes:
        return f"dentalapp:sensitive-data:v1:{purpose}".encode("ascii")


def build_sensitive_data_cipher(settings: Settings) -> SensitiveDataCipher:
    if not settings.patient_data_keys:
        raise SensitiveDataConfigurationError("PATIENT_DATA_KEYS yapılandırılmalıdır.")
    return SensitiveDataCipher(
        keys={
            key_id: _decode_key(value, setting_name=f"PATIENT_DATA_KEYS[{key_id}]")
            for key_id, value in settings.patient_data_keys.items()
        },
        active_key_id=settings.patient_data_active_key_id,
    )


@lru_cache
def get_sensitive_data_cipher() -> SensitiveDataCipher:
    return build_sensitive_data_cipher(get_settings())
