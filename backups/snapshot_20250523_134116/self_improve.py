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
            "Respond with a unified diff using GitHub style diffs."
        )
        raw = self.agent.ask_llm(prompt)
        # Debug: show raw LLM output
        print("[SelfImprove] Raw LLM output:\n", raw)

        # 2.5) extract diff
        m = re.search(r"```diff(.*?)```", raw, re.S)
        if m:
            diff_text = m.group(1).strip()
        else:
            lines = raw.splitlines()
            start = 0
            for i, line in enumerate(lines):
                if line.startswith('diff ') or line.startswith('--- ') or line.startswith('*** Begin Patch'):
                    start = i
                    break
            diff_text = '\n'.join(lines[start:]).strip()
        # Debug: show extracted diff
        print("[SelfImprove] Extracted diff:\n", diff_text)

        if not diff_text:
            print("[SelfImprove] No diff found; aborting self-improve.")
            return False

        # 3) dry-run patch
        strip = 1 if diff_text.startswith('diff ') else 0
        p = subprocess.Popen(
            ["patch", f"-p{strip}", "--dry-run"], stdin=subprocess.PIPE, text=True
        )
        dry_out, _ = p.communicate(diff_text)
        if p.returncode != 0:
            print("[SelfImprove] Patch dry-run failed; aborting self-improve.\n", dry_out)
            return False

        # 4) apply patch
        p = subprocess.Popen(
            ["patch", f"-p{strip}"], stdin=subprocess.PIPE, text=True
        )
        p.communicate(diff_text)
        if p.returncode != 0:
            print("[SelfImprove] Patch apply failed; restoring backup.")
            self._restore(backup_path)
            return False

        # 5) run tests
        res = subprocess.run(self.test_cmd, shell=True)
        if res.returncode != 0:
            print("[SelfImprove] Tests failed; restoring backup.")
            self._restore(backup_path)
            return False

        print("[SelfImprove] Success!")
        return True

    def _restore(self, backup_path):
        shutil.rmtree("app")
        shutil.copytree(backup_path, "app")
