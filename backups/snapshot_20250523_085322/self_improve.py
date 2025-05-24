import subprocess
import os
import shutil
from app.snapshot import SnapshotManager

class SelfImproveEngine:
    def __init__(self, agent, test_cmd="pytest"):
        self.agent = agent
        self.snapshot = SnapshotManager("app", "backups")
        self.test_cmd = test_cmd

    def run_cycle(self):
        # 1) backup
        backup_path = self.snapshot.create()

        # 2) ask LLM for improvements
        prompt = (
            "Review the entire contents of the `app/` folder in this project. "
            "Propose any code improvements (new features, refactorings, bug fixes). "
            "Supply a unified patch in diff format."
        )
        diff = self.agent.ask_llm(prompt)

        # 3) apply patch
        p = subprocess.Popen(
            ["patch", "-p1", "-d", "."], stdin=subprocess.PIPE, text=True
        )
        p.communicate(diff)
        if p.returncode != 0:
            self._restore(backup_path)
            return False

        # 4) run tests
        res = subprocess.run(self.test_cmd, shell=True)
        if res.returncode != 0:
            self._restore(backup_path)
            return False

        # success
        return True

    def _restore(self, backup_path):
        # wipe and restore
        shutil.rmtree("app")
        shutil.copytree(backup_path, "app")
