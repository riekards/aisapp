import os
import shutil
import tempfile
from app.snapshot import SnapshotManager

def test_snapshot_and_restore(tmp_path):
    # Create a fake app folder with one file
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "dummy.txt").write_text("version1")

    backup_dir = tmp_path / "backups"
    sm = SnapshotManager(str(app_dir), str(backup_dir))

    snap = sm.create()
    # File should exist in snapshot
    assert os.path.exists(os.path.join(snap, "dummy.txt"))

    # Modify original
    (app_dir / "dummy.txt").write_text("version2")
    # Restore
    sm = SnapshotManager(str(app_dir), str(backup_dir))
    sm.create()  # create a second snapshot just to test multiple
    # Manually restore from first snapshot
    shutil.rmtree(str(app_dir))
    shutil.copytree(snap, str(app_dir))
    assert (app_dir / "dummy.txt").read_text() == "version1"


def test_get_latest(tmp_path):
    app_dir = tmp_path / "app"
    backup_dir = tmp_path / "backups"
    app_dir.mkdir()
    (app_dir / "a.txt").write_text("v1")
    sm = SnapshotManager(str(app_dir), str(backup_dir))

    assert sm.get_latest() is None

    first = sm.create()
    (app_dir / "a.txt").write_text("v2")
    second = sm.create()

    latest = sm.get_latest()
    assert latest == second
