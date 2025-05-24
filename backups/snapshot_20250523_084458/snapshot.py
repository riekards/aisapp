import os
import shutil
from datetime import datetime

class SnapshotManager:
    def __init__(self, src_dir, backup_root):
        self.src_dir = src_dir
        self.backup_root = backup_root
        os.makedirs(self.backup_root, exist_ok=True)

    def create(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(self.backup_root, f"snapshot_{ts}")
        shutil.copytree(self.src_dir, dst)
        return dst
