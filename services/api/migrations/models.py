from sqlalchemy import MetaData

# This is a placeholder for SQLAlchemy models.
# The API gateway uses a lightweight schema managed via direct SQL.
# This metadata object is used by Alembic for autogenerate support.
target_metadata = MetaData()
