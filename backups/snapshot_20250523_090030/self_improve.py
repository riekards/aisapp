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

        # 2.5) extract diff
        # Try extracting between ```diff fences
        m = re.search(r"```diff(.*?)```", raw, re.S)
        if m:
            diff_text = m.group(1).strip()
        else:
            # Fallback: find first diff-like line
            lines = raw.splitlines()
            start = 0
            for i, line in enumerate(lines):
                if line.startswith('diff ') or line.startswith('--- ') or line.startswith('*** Begin Patch'):
                    start = i
                    break
            diff_text = '\n'.join(lines[start:]).strip()

        # Ensure we have diff content
        if not diff_text:
            print("No diff found; aborting self-improve.")
            return False

        # 3) dry-run patch with strip level auto-detect
        strip = 0
        if diff_text.startswith('diff '):
            strip = 1
        p = subprocess.Popen(
            ["patch", f"-p{strip}", "--dry-run"], stdin=subprocess.PIPE, text=True
        )
        dry_out, _ = p.communicate(diff_text)
        if p.returncode != 0:
            print("Patch dry-run failed; aborting self-improve.\n", dry_out)
            return False

        # 4) apply patch
        p = subprocess.Popen(
            ["patch", f"-p{strip}"], stdin=subprocess.PIPE, text=True
        )
        p.communicate(diff_text)
        if p.returncode != 0:
            self._restore(backup_path)
            return False

        # 5) run tests
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
