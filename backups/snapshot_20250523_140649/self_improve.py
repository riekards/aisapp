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

        # 2) Ask LLM for a unified diff for Python files under app/
        prompt = (
            "Review only the Python code in the app/ directory. "
            "Generate a unified diff (GitHub style) that applies to .py files under app/. "
            "Do not include any other files, commentary, or fences—only the raw diff lines."
        )
        raw = self.agent.ask_llm(prompt)
        print("[SelfImprove] Raw LLM output:\n", raw)

        # 3) Clean fences and comments
        lines = raw.splitlines()
        clean = []
        for line in lines:
            stripped = line.strip()
            # skip markdown fences and comment lines
            if stripped.startswith('```') or stripped.startswith('#'):
                continue
            clean.append(line)

        # 4) Extract diff lines: identify Python diff headers
        diff_started = False
        diff_lines = []
        for line in clean:
            if not diff_started:
                if line.startswith('diff ') and '.py' in line:
                    diff_started = True
                elif line.startswith('--- a/app/') and line.endswith('.py'):
                    diff_started = True
                else:
                    continue
            if diff_started:
                diff_lines.append(line)
        diff_text = '\n'.join(diff_lines).strip()
        print("[SelfImprove] Extracted diff:\n", diff_text)

        # Abort if nothing extracted
        if not diff_text:
            print("[SelfImprove] No diff found; aborting self-improve.")
            return False

        # 5) Determine strip level (-p)
        strip = 1 if diff_text.startswith('diff ') else 0

        # 6) Dry-run patch
        dry = subprocess.Popen([
            "patch", f"-p{strip}", "--dry-run"
        ], stdin=subprocess.PIPE, text=True)
        out, _ = dry.communicate(diff_text)
        if dry.returncode != 0:
            print("[SelfImprove] Patch dry-run failed; aborting.\n", out)
            return False

        # 7) Apply patch
        apply_proc = subprocess.Popen([
            "patch", f"-p{strip}"
        ], stdin=subprocess.PIPE, text=True)
        apply_proc.communicate(diff_text)
        if apply_proc.returncode != 0:
            print("[SelfImprove] Patch apply failed; restoring backup.")
            self._restore(backup_path)
            return False

        # 8) Run tests
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
