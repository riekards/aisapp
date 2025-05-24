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
        # 1) Backup current app folder
        backup_path = self.snapshot.create()

        # 2) Ask LLM for a unified diff (no commentary)
        prompt = (
            "Review the entire contents of the `app/` folder in this project. "
            "Propose any code improvements (new features, refactorings, bug fixes). "
            "Respond ONLY with a unified diff (GitHub style) without any explanatory text or Markdown fences."
        )
        raw = self.agent.ask_llm(prompt)
        # Debug output for diagnostics
        print("[SelfImprove] Raw LLM output:\n", raw)

        # 3) Extract diff content
        m = re.search(r"```?diff(.*?)```?", raw, re.S)
        if m:
            diff_text = m.group(1).strip()
        else:
            lines = raw.splitlines()
            start = 0
            for i, line in enumerate(lines):
                if line.startswith('diff ') or line.startswith('--- '):
                    start = i
                    break
            diff_text = '\n'.join(lines[start:]).strip()
        print("[SelfImprove] Extracted diff:\n", diff_text)

        if not diff_text:
            print("[SelfImprove] No diff found; aborting self-improve.")
            return False

        # 4) Determine strip level (-p)
        strip = 1 if diff_text.startswith('diff ') else 0

        # 5) Dry-run patch to validate
        dry = subprocess.Popen([
            "patch", f"-p{strip}", "--dry-run"
        ], stdin=subprocess.PIPE, text=True)
        out, err = dry.communicate(diff_text)
        if dry.returncode != 0:
            print("[SelfImprove] Patch dry-run failed; aborting self-improve.\n", out)
            return False

        # 6) Apply patch
        apply_proc = subprocess.Popen([
            "patch", f"-p{strip}"
        ], stdin=subprocess.PIPE, text=True)
        apply_proc.communicate(diff_text)
        if apply_proc.returncode != 0:
            print("[SelfImprove] Patch apply failed; restoring backup.")
            self._restore(backup_path)
            return False

        # 7) Run tests
        test_res = subprocess.run(self.test_cmd, shell=True)
        if test_res.returncode != 0:
            print("[SelfImprove] Tests failed; restoring backup.")
            self._restore(backup_path)
            return False

        print("[SelfImprove] Success!")
        return True

    def _restore(self, backup_path):
        # Restore app folder from backup
        shutil.rmtree("app")
        shutil.copytree(backup_path, "app")
