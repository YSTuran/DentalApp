import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import CaseFileVersion, CaseUploadSession, UploadStatus


def storage_report() -> dict[str, list[str]]:
    root = get_settings().storage_path.resolve()
    with SessionLocal() as db:
        expected_completed = set(db.scalars(select(CaseFileVersion.storage_key)).all())
        expected_temporary = set(
            db.scalars(
                select(CaseUploadSession.temp_storage_key).where(
                    CaseUploadSession.status.in_([UploadStatus.PENDING, UploadStatus.UPLOADING])
                )
            ).all()
        )

    expected = expected_completed | expected_temporary
    actual = {
        path.relative_to(root).as_posix()
        for folder in (root / "cases", root / "uploads")
        if folder.exists()
        for path in folder.rglob("*")
        if path.is_file()
    }
    return {
        "missing": sorted(expected - actual),
        "orphaned": sorted(actual - expected),
    }


def quarantine_orphans(paths: list[str]) -> Path | None:
    if not paths:
        return None
    root = get_settings().storage_path.resolve()
    target_root = root / "quarantine" / datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    for relative in paths:
        source = (root / relative).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            continue
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
    return target_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Veritabanındaki dosya kayıtlarını storage içeriğiyle karşılaştırır."
    )
    parser.add_argument(
        "--quarantine-orphans",
        action="store_true",
        help="Sahipsiz dosyaları silmeden storage/quarantine altına taşır.",
    )
    args = parser.parse_args()
    try:
        report = storage_report()
    except Exception as error:
        print(
            json.dumps(
                {
                    "error": "storage_check_unavailable",
                    "error_type": type(error).__name__,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 3
    if args.quarantine_orphans:
        target = quarantine_orphans(report["orphaned"])
        report["quarantined_to"] = [str(target)] if target else []
        report["orphaned"] = []
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["missing"]:
        return 2
    if report["orphaned"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
