import os
import shutil
import tempfile
import pytest
from app.self_improve import SelfImproveEngine
from app.agent import Agent

class DummyAgent(Agent):
    def __init__(self, patch_text, test_cmd="false"):
        # patch_text is a diff that modifies a file in app/
        self._patch = patch_text
        super().__init__()

    def ask_llm(self, prompt):
        return self._patch

@pytest.fixture
def simple_app(tmp_path, monkeypatch):
    # Create a fake app folder
    src = tmp_path / "src"
    src.mkdir()
    (src / "app").mkdir()
    (src / "app" / "file.txt").write_text("A")
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
