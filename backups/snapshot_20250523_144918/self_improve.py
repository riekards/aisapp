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

        # 2) Gather code context for self-improve prompt
        code_context = []
        for dirpath, _, files in os.walk('app'):
            for fname in files:
                if fname.endswith('.py'):
                    path = os.path.join(dirpath, fname)
                    try:
                        with open(path, 'r', encoding='utf-8') as cf:
                            content = cf.read()
                        code_context.append(f"### BEGIN {path}\n{content}\n### END {path}\n")
                    except Exception:
                        continue
        context_str = "".join(code_context)

        # 3) Ask LLM for a unified diff including feature requests and code context
        features = self.agent.get_features()
        feature_text = "\nImplement these features:\n" + "\n".join(f"- {f}" for f in features) if features else ""
        prompt = (
            context_str +
            "\nBased on the code above and the requested features, generate ONLY a unified diff (GitHub style) that applies to .py files under app/. "
            "Do NOT include any commentary or fences—only the raw diff lines." +
            feature_text
        )
        raw = self.agent.ask_llm(prompt)
        print("[SelfImprove] Raw LLM output:\n", raw)

        # 4) Clean raw output
        lines = raw.splitlines()
        clean = [l for l in lines if not l.strip().startswith(('```', '#'))]

        # 5) Split into diff chunks
        chunks = []
        current = []
        for line in clean:
            if line.startswith('diff '):
                if current:
                    chunks.append(current)
                current = [line]
            else:
                if current:
                    current.append(line)
        if current:
            chunks.append(current)

        # 6) Filter chunks for existing files
        valid_chunks = []
        for chunk in chunks:
            header = chunk[0]
            m = re.match(r"diff --git a/(?P<path>app/.*\.py) b/", header)
            if not m:
                continue
            rel_path = m.group('path')
            if os.path.exists(rel_path):
                valid_chunks.append('\n'.join(chunk))
            else:
                print(f"[SelfImprove] Skipping diff for missing file: {rel_path}")

        diff_text = '\n'.join(valid_chunks).strip()
        print("[SelfImprove] Filtered diff:\n", diff_text)

        if not diff_text:
            print("[SelfImprove] No valid diffs; aborting self-improve.")
            return False

        # 7) Dry-run patch
        strip = 1
        dry = subprocess.Popen([
            "patch", f"-p{strip}", "--dry-run"
        ], stdin=subprocess.PIPE, text=True)
        out, _ = dry.communicate(diff_text)
        if dry.returncode != 0:
            print("[SelfImprove] Patch dry-run failed; aborting.\n", out)
            return False

        # 8) Apply patch
        proc = subprocess.Popen([
            "patch", f"-p{strip}"
        ], stdin=subprocess.PIPE, text=True)
        proc.communicate(diff_text)
        if proc.returncode != 0:
            print("[SelfImprove] Patch apply failed; restoring backup.")
            self._restore(backup_path)
            return False

        # 9) Run tests
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
