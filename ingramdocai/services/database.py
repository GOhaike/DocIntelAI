from ingramdocai.persistence.db import SessionLocal

def get_db_session():
    """Returns a new SQLAlchemy session."""
    return SessionLocal()
