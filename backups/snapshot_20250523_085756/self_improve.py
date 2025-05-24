import subprocess
import os
import shutil
import re
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
            "Respond with a unified diff using GitHub style, including ```diff fences."
        )
        raw = self.agent.ask_llm(prompt)

        # 2.5) extract diff between ```diff fences
        m = re.search(r"```diff(.*?)```", raw, re.S)
        diff_text = m.group(1).strip() if m else raw

        # 3) apply patch with strip level 0
        p = subprocess.Popen(
            ["patch", "-p0", "--dry-run"], stdin=subprocess.PIPE, text=True
        )
        dry_out, _ = p.communicate(diff_text)
        if p.returncode != 0:
            # malformed or doesn't apply
            print("Patch dry-run failed; aborting self-improve.\n", dry_out)
            return False

        # actually apply
        p = subprocess.Popen(
            ["patch", "-p0"], stdin=subprocess.PIPE, text=True
        )
        p.communicate(diff_text)
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
