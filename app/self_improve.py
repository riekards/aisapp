import subprocess
import os
import shutil
import re

from app.snapshot import SnapshotManager

class SelfImproveEngine:
    def __init__(self, agent, use_real_llm: bool = True, test_cmd="pytest", skip_backups: bool = False):
        self.agent = agent
        self.snapshot = SnapshotManager("app", "backups")
        self.test_cmd = test_cmd
        self.skip_backups = skip_backups

    def run_cycle(self):
        # 1) Take a snapshot of current app/ for rollback
        if not self.skip_backups:
            backup_path = self.snapshot.create()
        else:
            backup_path = self.snapshot.get_latest() or self.snapshot.create()

        # 2) Collect code context and file list
        code_snippets = []
        file_list = []
        for dirpath, _, files in os.walk('app'):
            for fname in files:
                if fname.endswith('.py'):
                    rel_path = os.path.join(dirpath, fname).replace('\\', '/')
                    file_list.append(rel_path)
                    try:
                        with open(rel_path, 'r', encoding='utf-8') as f:
                            code_snippets.append(f"### FILE: {rel_path}\n{f.read()}\n")
                    except Exception:
                        continue
        files_header = "\n".join(f"- {p}" for p in file_list)
        context = "".join(code_snippets)

        # 3) Build a precise prompt that references actual file names and contents
        features = self.agent.get_features()
        feature_block = ''
        if features:
            feature_block = "Implement these features using existing code structure:\n" + \
                "\n".join(f"* {f}" for f in features) + "\n"

        prompt = (
            "You have these Python files (paths + contents):\n"
            f"{files_header}\n\n"
            f"{context}\n\n"
            "Implement these feature requests exactly:\n"
            + "\n".join(f"- {f}" for f in features) + "\n\n"
            "Now, produce *only* a unified Git diff (GitHub style) that "
            "modifies or creates any needed .py files under app/ to satisfy "
            "those requests. Do NOT output any explanations, commentary, or "
            "fences—output must start with `diff --git a/...` and be valid "
            "patch input to `patch -p1`."
        )

        raw_diff = self.agent.ask_llm(prompt)
        print("[SelfImprove] Raw diff from LLM:\n", raw_diff)

        # 4) Clean diff: remove any fences or notes
        lines = raw_diff.splitlines()
        diff_lines = [l for l in lines if not re.match(r'^(```|Note:|#)', l.strip())]

        # 5) Split into diff chunks
        chunks = []
        current = []
        for line in diff_lines:
            if line.startswith('diff --git '):
                if current:
                    chunks.append(current)
                current = [line]
            elif current:
                current.append(line)
        if current:
            chunks.append(current)

        # 6) Keep only chunks for existing or new .py files under app/
        valid_chunks = []
        for chunk in chunks:
            header = chunk[0]
            m = re.search(r'diff --git a/(?P<path>app/.*\.py) b/(?P<path2>app/.*\.py)', header)
            if m:
                path = m.group('path')
                # accept both new and existing files
                valid_chunks.append("\n".join(chunk))
            else:
                continue

        diff_text = "\n".join(valid_chunks)
        print("[SelfImprove] Filtered diff to apply:\n", diff_text)
        if not diff_text.strip():
            print("[SelfImprove] No valid diff found; aborting self-improve.")
            return False

        # 7) Dry-run patch
        strip = 1
        dry = subprocess.Popen(["patch", f"-p{strip}", "--dry-run"], stdin=subprocess.PIPE, text=True)
        out, _ = dry.communicate(diff_text)
        if dry.returncode != 0:
            print("[SelfImprove] Patch dry-run failed:\n", out)
            return False

        # 8) Apply patch
        try:
            patch_result = self._apply_patch(diff_text)
            if not patch_result:
                return 'Fail'

            # 9) Run tests
            test_result = self._run_tests()
            if test_result.returncode == 0:
                return 'Success'
            elif test_result.returncode < 2:
                return 'Partial'
            return 'Fail'
        except Exception as e:
            print(f"Error in improvement cycle: {e}")
            return 'Fail'

    def _restore(self, backup_path):
        shutil.rmtree('app')
        shutil.copytree(backup_path, 'app')
