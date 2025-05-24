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

        # 3) Build prompt
        features = self.agent.get_features()
        feature_text = "\nImplement these features:\n" + "\n".join(f"- {f}" for f in features) if features else ""
        prompt = (
            context_str +
            "Based on the code above and the requested features, produce a unified diff (GitHub style) that directly modifies or creates only the necessary Python files under app/. "
            "Include pytest test files for all new functionality. "
            "Output ONLY the diff text (no explanations, commentary, or code blocks)." +
            feature_text
        )
        raw = self.agent.ask_llm(prompt)
        print("[SelfImprove] Raw LLM output:\n", raw)

        # 4) Clean raw output
        lines = raw.splitlines()
        clean = [l for l in lines if not l.strip().startswith(('```', '#', 'Note:'))]

        # 5) Normalize and split into diff chunks
        chunks = []
        current = []
        for line in clean:
            if line.startswith('diff --git '):
                if current:
                    chunks.append(current)
                # normalize header to use same path on both sides
                m = re.match(r'diff --git a/(?P<path>app/.*\.py) b/.*', line)
                if m:
                    path = m.group('path')
                    header = f'diff --git a/{path} b/{path}'
                else:
                    header = line
                current = [header]
            elif current:
                # normalize --- and +++ lines
                if line.startswith('--- '):
                    # always map to a/<path>
                    parts = line.split()
                    rel = parts[1].split('/')[-2:]
                    current.append(f'--- a/{"/".join(rel)}')
                elif line.startswith('+++ '):
                    parts = line.split()
                    rel = parts[1].split('/')[-2:]
                    current.append(f'+++ b/{"/".join(rel)}')
                else:
                    current.append(line)
        if current:
            chunks.append(current)

        # 6) Filter for existing files
        valid = []
        for chunk in chunks:
            header = chunk[0]
            m = re.match(r'diff --git a/(?P<path>app/.*\.py) b/', header)
            if not m:
                continue
            path = m.group('path')
            if os.path.exists(path):
                valid.append('\n'.join(chunk))
            else:
                print(f"[SelfImprove] Skipping missing file: {path}")

        diff_text = '\n'.join(valid)
        print("[SelfImprove] Filtered diff:\n", diff_text)
        if not diff_text:
            print("[SelfImprove] No valid diffs; aborting.")
            return False

        # 7) Dry-run
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
            print("[SelfImprove] Patch apply failed; restoring.")
            self._restore(backup_path)
            return False

        # 9) Test
        res = subprocess.run(self.test_cmd, shell=True)
        if res.returncode != 0:
            print("[SelfImprove] Tests failed; restoring.")
            self._restore(backup_path)
            return False

        print("[SelfImprove] Success!")
        return True

    def _restore(self, backup_path):
        shutil.rmtree("app")
        shutil.copytree(backup_path, "app")
