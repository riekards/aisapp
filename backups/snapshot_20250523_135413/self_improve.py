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

        # 2) Ask LLM for a unified diff (Python-only, GitHub style)
        prompt = (
            "Review only the Python code in the app/ directory. "
            "Generate a unified diff (GitHub style) that applies to .py files under app/. "
            "Do not include any other files, commentary, or fences—only the raw diff lines."
        )
        raw = self.agent.ask_llm(prompt)
        print("[SelfImprove] Raw LLM output:\n", raw)

        # 3) Extract diff lines: start at first file path under app/
        lines = raw.splitlines()
        diff_started = False
        diff_lines = []
        for line in lines:
            # begin when a valid Python patch header appears
            if not diff_started and re.match(r"^(?:diff --git a/app/.*\.py b/app/.*\.py)$", line):
                diff_started = True
                diff_lines.append(line)
                continue
            if diff_started:
                diff_lines.append(line)
        diff_text = '\n'.join(diff_lines).strip()
        print("[SelfImprove] Extracted diff:\n", diff_text)

        if not diff_text:
            print("[SelfImprove] No diff found; aborting self-improve.")
            return False

        # 4) Determine strip level for paths starting with a/app/
        strip = 1 if diff_text.startswith('diff ') else 0

        # 5) Dry-run patch
        dry = subprocess.Popen([
            "patch", f"-p{strip}", "--dry-run"
        ], stdin=subprocess.PIPE, text=True)
        out, _ = dry.communicate(diff_text)
        if dry.returncode != 0:
            print("[SelfImprove] Patch dry-run failed; aborting.\n", out)
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
