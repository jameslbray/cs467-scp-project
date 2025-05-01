# shared/db/base.py

from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import MetaData

# Single metadata for all services
metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata

    @declared_attr
    def __tablename__(cls) -> str:
        # automatic table naming: class name lowercase
        return cls.__name__.lower()
