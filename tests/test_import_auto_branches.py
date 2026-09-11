"""US-001: prb_import_auto_branches repository."""

from __future__ import annotations

from app.repositories.import_repository import ImportRepository


def test_auto_branches_insert_and_list_roundtrip():
    repo = ImportRepository()
    batch = repo.create_batch(
        file_name="auto_branch_test.csv",
        file_ext=".csv",
        file_size_bytes=10,
        file_path="/tmp/auto_branch_test.csv",
        file_mtime=None,
        actor="test_auto_branches",
    )
    batch_id = int(batch["id"])
    repo.clear_auto_branches(batch_id)
    assert repo.list_auto_branches(batch_id) == []

    row = repo.insert_auto_branch(
        batch_id=batch_id,
        branch="TMB TESTE AUTO",
        login="testeauto",
        user_id=None,
        actor="test_auto_branches",
    )
    assert row["branch"] == "TMB TESTE AUTO"
    assert row["login"] == "testeauto"
    assert int(row["batch_id"]) == batch_id

    listed = repo.list_auto_branches(batch_id)
    assert len(listed) == 1
    assert listed[0]["branch"] == "TMB TESTE AUTO"

    # unique (batch_id, branch) — upsert não duplica
    repo.insert_auto_branch(
        batch_id=batch_id,
        branch="TMB TESTE AUTO",
        login="testeauto2",
        user_id=None,
        actor="test_auto_branches",
    )
    listed2 = repo.list_auto_branches(batch_id)
    assert len(listed2) == 1
    assert listed2[0]["login"] == "testeauto2"
