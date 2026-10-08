import sys

from app.cli import check_storage


def test_storage_check_returns_distinct_code_when_inspection_cannot_run(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(sys, "argv", ["check_storage"])
    monkeypatch.setattr(
        check_storage,
        "storage_report",
        lambda: (_ for _ in ()).throw(RuntimeError("database schema missing")),
    )

    assert check_storage.main() == 3
    assert "storage_check_unavailable" in capsys.readouterr().err


def test_storage_check_keeps_orphan_exit_code(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["check_storage"])
    monkeypatch.setattr(
        check_storage,
        "storage_report",
        lambda: {"missing": [], "orphaned": ["cases/orphan.stl"]},
    )

    assert check_storage.main() == 1
    assert "cases/orphan.stl" in capsys.readouterr().out
