from shackles import models  # noqa: F401
from shackles.db.base import Base

print("Tables:", sorted(Base.metadata.tables.keys()))