from sqlalchemy import create_engine, Column, Integer, String, Text, Table, MetaData
from sqlalchemy.orm import sessionmaker

class Memory:
    def __init__(self, db_path: str = "memory.db"):
        # Initialize database engine and metadata
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.meta = MetaData()

        # Define messages table
        self.messages = Table(
            "messages", self.meta,
            Column("id", Integer, primary_key=True),
            Column("role", String, nullable=False),
            Column("content", Text, nullable=False),
        )

        # Define features table
        self.features = Table(
            "features", self.meta,
            Column("id", Integer, primary_key=True),
            Column("description", Text, unique=True, nullable=False),
        )

        # Define scores table for RL rewards
        self.scores = Table(
            "scores", self.meta,
            Column("id", Integer, primary_key=True),
            Column("value", Integer, default=0),
        )

        # Create all tables if they do not exist
        self.meta.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_message(self, role: str, content: str):
        """Persist a chat message (user or AI)."""
        session = self.Session()
        session.execute(
            self.messages.insert().values(role=role, content=content)
        )
        session.commit()
        session.close()

    def list_messages(self) -> list[dict]:
        """Retrieve all messages as list of dicts."""
        session = self.Session()
        rows = session.execute(self.messages.select()).fetchall()
        session.close()
        return [{"id": r.id, "role": r.role, "content": r.content} for r in rows]

    def save_feature(self, description: str):
        """Add a new feature request if not already present."""
        session = self.Session()
        try:
            session.execute(self.features.insert().values(description=description))
            session.commit()
        except Exception:
            session.rollback()  # likely duplicate
        finally:
            session.close()

    def list_features(self) -> list[str]:
        """Get all pending feature descriptions."""
        session = self.Session()
        rows = session.execute(self.features.select()).fetchall()
        session.close()
        return [r.description for r in rows]

    def delete_feature(self, feature_id: int):
        """Remove a feature by its ID."""
        session = self.Session()
        session.execute(
            self.features.delete().where(self.features.c.id == feature_id)
        )
        session.commit()
        session.close()

    def add_reward(self, delta: int):
        """Update cumulative reward score."""
        session = self.Session()
        # Check if a score row exists
        row = session.execute(self.scores.select()).first()
        if row:
            new_val = row.value + delta
            session.execute(
                self.scores.update().values(value=new_val).where(self.scores.c.id == row.id)
            )
        else:
            # First reward entry
            session.execute(self.scores.insert().values(value=delta))
        session.commit()
        session.close()

    def get_score(self) -> int:
        """Retrieve the current cumulative reward score."""
        session = self.Session()
        row = session.execute(self.scores.select()).first()
        session.close()
        return row.value if row else 0
