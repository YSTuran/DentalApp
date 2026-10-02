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

    def sanitize_stl_metadata(self, storage_key: str) -> bool:
        """Remove names from binary headers and ASCII solid declarations in-place."""
        path = self.path_for(storage_key)
        try:
            size = path.stat().st_size
            with path.open("r+b") as handle:
                header = handle.read(84)
                if len(header) >= 84:
                    triangle_count = int.from_bytes(header[80:84], "little")
                    if size == 84 + triangle_count * 50:
                        sanitized_header = b"DentalApp sanitized STL".ljust(80, b" ")
                        changed = header[:80] != sanitized_header
                        if changed:
                            handle.seek(0)
                            handle.write(sanitized_header)
                            handle.flush()
                            os.fsync(handle.fileno())
                        return changed

                handle.seek(0)
                first_block = handle.read(min(size, 4096))
                leading = len(first_block) - len(first_block.lstrip())
                if not first_block[leading:].lower().startswith(b"solid"):
                    return False

                changed = self._redact_ascii_name(
                    handle,
                    block=first_block,
                    block_offset=0,
                    keyword=b"solid",
                )
                tail_offset = max(0, size - 4096)
                handle.seek(tail_offset)
                tail_block = handle.read(size - tail_offset)
                changed = self._redact_ascii_name(
                    handle,
                    block=tail_block,
                    block_offset=tail_offset,
                    keyword=b"endsolid",
                    use_last=True,
                ) or changed
                if changed:
                    handle.flush()
                    os.fsync(handle.fileno())
                return changed
        except FileNotFoundError as error:
            raise StorageError("Depolanan dosya bulunamadı.") from error
        except OSError as error:
            raise StorageError("STL üst verisi temizlenemedi.") from error

    @staticmethod
    def _redact_ascii_name(
        handle,
        *,
        block: bytes,
        block_offset: int,
        keyword: bytes,
        use_last: bool = False,
    ) -> bool:
        lowered = block.lower()
        start = lowered.rfind(keyword) if use_last else lowered.find(keyword)
        if start < 0:
            return False
        name_start = start + len(keyword)
        line_end_candidates = [
            position
            for marker in (b"\r", b"\n")
            if (position := block.find(marker, name_start)) >= 0
        ]
        line_end = min(line_end_candidates, default=len(block))
        if line_end <= name_start:
            return False
        current = block[name_start:line_end]
        if not current.strip():
            return False
        replacement = bytearray(b" " * len(current))
        label = b" dentalapp"[: len(replacement)]
        replacement[: len(label)] = label
        handle.seek(block_offset + name_start)
        handle.write(replacement)
        return current != replacement

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
