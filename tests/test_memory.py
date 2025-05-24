import os
import shutil
import tempfile
import pytest
from app.memory import Memory
from sqlalchemy.exc import IntegrityError

@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_mem.db")

def test_save_and_list_messages(db_path):
    mem = Memory(db_path)
    mem.save_message("user", "hello")
    mem.save_message("ai", "hi there")

    # Directly query the messages table
    msgs = list(mem.Session().query(mem.messages).all())
    roles = [m.role for m in msgs]
    contents = [m.content for m in msgs]
    assert "user" in roles and "ai" in roles
    assert "hello" in contents and "hi there" in contents

def test_unique_feature_descriptions(db_path):
    mem = Memory(db_path)
    # First insert should work
    session = mem.Session()
    session.execute(mem.features.insert().values(description="feat1"))
    session.commit()

    # Duplicate should raise IntegrityError
    with pytest.raises(IntegrityError):
        session.execute(mem.features.insert().values(description="feat1"))
        session.commit()
