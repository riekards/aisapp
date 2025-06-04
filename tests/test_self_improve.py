import os
import shutil
import tempfile
import pytest
from app.self_improve import SelfImproveEngine

class DummyAgent:
    def __init__(self, patch_text):
        self._patch = patch_text

    def ask_llm(self, prompt):
        return self._patch

    def get_features(self):
        return []

@pytest.fixture
def simple_app(tmp_path, monkeypatch):
    # Create a fake app folder
    src = tmp_path / "src"
    src.mkdir()
    (src / "app").mkdir()
    (src / "app" / "file.txt").write_text("A\n")
    # Redirect SnapshotManager to work under tmp_path
    monkeypatch.chdir(str(tmp_path))
    return str(src)

def test_self_improve_revert(tmp_path, simple_app):
    # A patch that introduces a syntax error
    bad_patch = """\
*** Begin Patch
*** Update File: app/file.txt
@@ -1 +1 @@
-A
+B
*** End Patch
"""
    engine = SelfImproveEngine(DummyAgent(bad_patch), test_cmd="pytest")  # pytest will fail on any test
    os.makedirs("app", exist_ok=True)
    shutil.copytree(os.path.join(simple_app, "app"), "app", dirs_exist_ok=True)
    # No tests exist, pytest will halt with exit code != 0
    result = engine.run_cycle()
    assert result is False or result == 'fail'
    # file.txt should still contain "A"
    assert open("app/file.txt").read().strip() == "A"


def test_apply_patch_success(tmp_path, simple_app):
    patch = (
        "diff --git a/app/file.txt b/app/file.txt\n"
        "--- a/app/file.txt\n"
        "+++ b/app/file.txt\n"
        "@@ -1 +1 @@\n"
        "-A\n"
        "+B\n"
        ""
    )
    engine = SelfImproveEngine(DummyAgent(""), test_cmd="true")
    os.makedirs("app", exist_ok=True)
    shutil.copytree(os.path.join(simple_app, "app"), "app", dirs_exist_ok=True)
    result = engine._apply_patch(patch)
    assert result is True
    assert open("app/file.txt").read().strip() == "B"


def test_run_tests_executes_command(tmp_path):
    engine = SelfImproveEngine(DummyAgent(""), test_cmd="true")
    res = engine._run_tests()
    assert res.returncode == 0

    engine_fail = SelfImproveEngine(DummyAgent(""), test_cmd="false")
    res2 = engine_fail._run_tests()
    assert res2.returncode != 0
