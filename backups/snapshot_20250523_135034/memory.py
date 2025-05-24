from sqlalchemy import create_engine, Column, Integer, String, Text, Table, MetaData
from sqlalchemy.orm import sessionmaker

class Memory:
    def __init__(self, db_path="memory.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.meta = MetaData()
        self.messages = Table(
            "messages", self.meta,
            Column("id", Integer, primary_key=True),
            Column("role", String),
            Column("content", Text),
        )
        self.features = Table(
            "features", self.meta,
            Column("id", Integer, primary_key=True),
            Column("description", Text, unique=True),
        )
        self.meta.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_message(self, role, content):
        session = self.Session()
        session.execute(self.messages.insert().values(role=role, content=content))
        session.commit()
        session.close()

    def list_features(self):
        session = self.Session()
        rows = session.query(self.features).all()
        session.close()
        return [r.description for r in rows]
