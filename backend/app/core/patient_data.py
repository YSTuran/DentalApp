import base64
import hashlib
import hmac
import os
import unicodedata
from collections.abc import Mapping
from functools import lru_cache
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings, get_settings

ENVELOPE_PREFIX = b"DP1"
NONCE_BYTES = 12
ALLOWED_FIELDS = frozenset({"patient_code", "patient_name"})


class PatientDataConfigurationError(RuntimeError):
    pass


class PatientDataIntegrityError(RuntimeError):
    pass


def normalize_patient_code(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def _decode_key(value: str, *, setting_name: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise PatientDataConfigurationError(
            f"{setting_name} geçerli Base64 biçiminde olmalıdır."
        ) from error
    if len(decoded) != 32:
        raise PatientDataConfigurationError(f"{setting_name} tam olarak 32 bayt olmalıdır.")
    return decoded


class PatientDataCipher:
    def __init__(
        self,
        *,
        keys: Mapping[str, bytes],
        active_key_id: str,
        lookup_key: bytes,
    ) -> None:
        if active_key_id not in keys:
            raise PatientDataConfigurationError("Etkin hasta verisi anahtarı bulunamadı.")
        try:
            valid_key_ids = all(0 < len(key_id.encode("ascii")) <= 32 for key_id in keys)
        except UnicodeEncodeError as error:
            raise PatientDataConfigurationError(
                "Anahtar kimlikleri yalnızca ASCII karakter içermelidir."
            ) from error
        if not valid_key_ids:
            raise PatientDataConfigurationError("Anahtar kimlikleri 1-32 ASCII karakter olmalıdır.")
        if any(len(key) != 32 for key in keys.values()) or len(lookup_key) != 32:
            raise PatientDataConfigurationError("Hasta verisi anahtarları 32 bayt olmalıdır.")
        self._keys = dict(keys)
        self._active_key_id = active_key_id
        self._lookup_key = lookup_key

    def encrypt(self, value: str, *, case_id: UUID, field: str) -> bytes:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Boş metin şifrelenemez.")
        key_id = self._active_key_id.encode("ascii")
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = AESGCM(self._keys[self._active_key_id]).encrypt(
            nonce,
            normalized_value.encode("utf-8"),
            self._associated_data(case_id, field),
        )
        return ENVELOPE_PREFIX + bytes([len(key_id)]) + key_id + nonce + ciphertext

    def decrypt(self, envelope: bytes, *, case_id: UUID, field: str) -> str:
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
            key = self._keys[key_id]
            plaintext = AESGCM(key).decrypt(
                envelope[nonce_start:ciphertext_start],
                envelope[ciphertext_start:],
                self._associated_data(case_id, field),
            )
            return plaintext.decode("utf-8")
        except (IndexError, InvalidTag, KeyError, UnicodeDecodeError, ValueError) as error:
            raise PatientDataIntegrityError(
                "Hasta verisi çözülemedi veya bütünlük kontrolü başarısız oldu."
            ) from error

    def lookup_digest(self, patient_code: str) -> bytes:
        normalized = normalize_patient_code(patient_code)
        return hmac.new(self._lookup_key, normalized.encode("utf-8"), hashlib.sha256).digest()

    @staticmethod
    def _associated_data(case_id: UUID, field: str) -> bytes:
        if field not in ALLOWED_FIELDS:
            raise ValueError("Desteklenmeyen hasta verisi alanı.")
        return f"dentalapp:patient-data:v1:{case_id}:{field}".encode()


def build_patient_data_cipher(settings: Settings) -> PatientDataCipher:
    if not settings.patient_data_keys or not settings.patient_lookup_key:
        raise PatientDataConfigurationError(
            "PATIENT_DATA_KEYS ve PATIENT_LOOKUP_KEY yapılandırılmalıdır."
        )
    keys = {
        key_id: _decode_key(value, setting_name=f"PATIENT_DATA_KEYS[{key_id}]")
        for key_id, value in settings.patient_data_keys.items()
    }
    return PatientDataCipher(
        keys=keys,
        active_key_id=settings.patient_data_active_key_id,
        lookup_key=_decode_key(settings.patient_lookup_key, setting_name="PATIENT_LOOKUP_KEY"),
    )


@lru_cache
def get_patient_data_cipher() -> PatientDataCipher:
    return build_patient_data_cipher(get_settings())
