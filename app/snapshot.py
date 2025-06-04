import os
import shutil
from datetime import datetime

class SnapshotManager:
    def __init__(self, src_dir: str, backup_dir: str):
        self.src_dir = src_dir
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def create(self) -> str:
        """
        Copy the entire src_dir into a timestamped folder under backup_dir.
        Returns the path to the new snapshot folder.
        """
        now = datetime.utcnow()
        base = now.strftime("snapshot_%Y%m%d_%H%M%S")
        dst = os.path.join(self.backup_dir, base)
        i = 1
        # ensure unique folder name
        while os.path.exists(dst):
            dst = os.path.join(self.backup_dir, f"{base}_{i}")
            i += 1
        shutil.copytree(self.src_dir, dst)
        return dst

    def get_latest(self) -> str | None:
        """Return the most recently created snapshot directory or None."""
        candidates = []
        for name in os.listdir(self.backup_dir):
            path = os.path.join(self.backup_dir, name)
            if os.path.isdir(path) and name.startswith("snapshot_"):
                candidates.append(path)
        if not candidates:
            return None
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return candidates[0]

    def restore(self, snapshot_path: str):
        """
        Restore the src_dir from a given snapshot folder.
        """
        if os.path.exists(self.src_dir):
            shutil.rmtree(self.src_dir)
        shutil.copytree(snapshot_path, self.src_dir)
