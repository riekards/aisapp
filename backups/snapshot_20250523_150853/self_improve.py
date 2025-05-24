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

        # 2) Gather full code context
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

        # 3) Build precise prompt
        features = self.agent.get_features()
        feature_block = ''
        if features:
            feature_block = "Implement these features:\n" + "\n".join(f"- {f}" for f in features) + "\n"

        prompt = (
            context_str +
            "\nBased on the code above and the requested features, generate i) only a unified diff in GitHub style that modifies or creates necessary Python modules under app/, including corresponding pytest tests; ii) do not include any commentary, explanations, or markdown fences.\n" +
            feature_block
        )

        raw = self.agent.ask_llm(prompt)
        print("[SelfImprove] Raw output:\n", raw)

        # 4) Clean diff text
        lines = raw.splitlines()
        clean = [l for l in lines if not re.match(r'^(```|#|Note:)', l.strip())]

        # 5) Split and normalize chunks
        chunks, current = [], []
        for line in clean:
            if line.startswith('diff --git'):
                if current:
                    chunks.append(current)
                current = [line]
            elif current:
                current.append(line)
        if current:
            chunks.append(current)

        # 6) Filter valid files
        valid = []
        for chunk in chunks:
            header = chunk[0]
            m = re.match(r'diff --git a/(?P<path>app/.*\.py) b/', header)
            if not m:
                continue
            path = m.group('path')
            if os.path.exists(path):
                # normalize header paths
                chunk[0] = f'diff --git a/{path} b/{path}'
                # normalize --- +++ lines
                for i, l in enumerate(chunk):
                    if l.startswith('--- '):
                        chunk[i] = f'--- a/{path}'
                    if l.startswith('+++ '):
                        chunk[i] = f'+++ b/{path}'
                valid.append("\n".join(chunk))
            else:
                print(f"[SelfImprove] Skipping missing: {path}")

        diff_text = "\n".join(valid)
        print("[SelfImprove] Filtered diff:\n", diff_text)
        if not diff_text:
            print("[SelfImprove] Aborting: no valid diff.")
            return False

        # 7) Patch dry-run
        strip = 1
        p = subprocess.Popen(["patch", f"-p{strip}", "--dry-run"], stdin=subprocess.PIPE, text=True)
        out, _ = p.communicate(diff_text)
        if p.returncode != 0:
            print("[SelfImprove] Dry-run failed:\n", out)
            return False

        # 8) Apply patch
        p = subprocess.Popen(["patch", f"-p{strip}"], stdin=subprocess.PIPE, text=True)
        p.communicate(diff_text)
        if p.returncode != 0:
            print("[SelfImprove] Patch failed; restoring.")
            self._restore(backup_path)
            return False

        # 9) Run tests
        res = subprocess.run(self.test_cmd, shell=True)
        if res.returncode != 0:
            print("[SelfImprove] Tests failed; restoring.")
            self._restore(backup_path)
            return False

        print("[SelfImprove] Success!")
        return True

    def _restore(self, backup_path):
        shutil.rmtree('app')
        shutil.copytree(backup_path, 'app')
