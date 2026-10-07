from typing import Any

from sqlalchemy import LargeBinary
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator

from app.core.sensitive_data import get_sensitive_data_cipher


class EncryptedText(TypeDecorator[str]):
    impl = LargeBinary
    cache_ok = True

    def __init__(self, purpose: str) -> None:
        super().__init__()
        self.purpose = purpose

    def process_bind_param(self, value: str | None, dialect: Dialect) -> bytes | None:
        del dialect
        if value is None:
            return None
        return get_sensitive_data_cipher().encrypt_text(value, purpose=self.purpose)

    def process_result_value(self, value: bytes | None, dialect: Dialect) -> str | None:
        del dialect
        if value is None:
            return None
        return get_sensitive_data_cipher().decrypt_text(bytes(value), purpose=self.purpose)


class EncryptedJSON(TypeDecorator[Any]):
    impl = LargeBinary
    cache_ok = True

    def __init__(self, purpose: str) -> None:
        super().__init__()
        self.purpose = purpose

    def process_bind_param(self, value: Any, dialect: Dialect) -> bytes | None:
        del dialect
        if value is None:
            return None
        return get_sensitive_data_cipher().encrypt_json(value, purpose=self.purpose)

    def process_result_value(self, value: bytes | None, dialect: Dialect) -> Any:
        del dialect
        if value is None:
            return None
        return get_sensitive_data_cipher().decrypt_json(bytes(value), purpose=self.purpose)
