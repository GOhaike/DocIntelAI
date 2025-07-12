from persistence.db import engine
from persistence.models import Base

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Document_sessions table created.")

if __name__ == "__main__":
    init_db()
