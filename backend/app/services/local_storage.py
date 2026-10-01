import hashlib
import os
from pathlib import Path


class StorageError(RuntimeError):
    pass


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, storage_key: str) -> Path:
        relative = Path(storage_key)
        if relative.is_absolute() or ".." in relative.parts:
            raise StorageError("Geçersiz depolama anahtarı.")
        candidate = (self.root / relative).resolve()
        if not candidate.is_relative_to(self.root):
            raise StorageError("Depolama anahtarı izin verilen dizinin dışında.")
        return candidate

    def create_empty(self, storage_key: str) -> None:
        path = self.path_for(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.touch(exist_ok=False)
        except FileExistsError as error:
            raise StorageError("Geçici yükleme dosyası zaten var.") from error

    def append(self, storage_key: str, *, offset: int, data: bytes) -> int:
        path = self.path_for(storage_key)
        try:
            with path.open("r+b") as handle:
                handle.seek(0, os.SEEK_END)
                actual_size = handle.tell()
                if actual_size < offset:
                    raise StorageError("Geçici dosyanın boyutu yükleme kaydıyla uyuşmuyor.")
                if actual_size > offset:
                    handle.truncate(offset)
                handle.seek(offset)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
                return handle.tell()
        except FileNotFoundError as error:
            raise StorageError("Geçici yükleme dosyası bulunamadı.") from error

    def truncate(self, storage_key: str, size: int) -> None:
        path = self.path_for(storage_key)
        with path.open("r+b") as handle:
            handle.truncate(size)
            handle.flush()
            os.fsync(handle.fileno())

    def size(self, storage_key: str) -> int:
        try:
            return self.path_for(storage_key).stat().st_size
        except FileNotFoundError as error:
            raise StorageError("Depolanan dosya bulunamadı.") from error

    def sha256(self, storage_key: str) -> str:
        digest = hashlib.sha256()
        try:
            with self.path_for(storage_key).open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
        except FileNotFoundError as error:
            raise StorageError("Depolanan dosya bulunamadı.") from error
        return digest.hexdigest()

    def promote(self, temporary_key: str, final_key: str) -> None:
        temporary_path = self.path_for(temporary_key)
        final_path = self.path_for(final_key)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if final_path.exists():
            raise StorageError("Hedef depolama anahtarı zaten kullanılıyor.")
        try:
            os.replace(temporary_path, final_path)
        except FileNotFoundError as error:
            raise StorageError("Geçici yükleme dosyası bulunamadı.") from error

    def restore(self, final_key: str, temporary_key: str) -> None:
        final_path = self.path_for(final_key)
        temporary_path = self.path_for(temporary_key)
        temporary_path.parent.mkdir(parents=True, exist_ok=True)
        if final_path.exists():
            os.replace(final_path, temporary_path)

    def remove(self, storage_key: str) -> None:
        self.path_for(storage_key).unlink(missing_ok=True)
