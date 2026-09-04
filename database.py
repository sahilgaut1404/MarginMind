from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base,sessionmaker

DATABASE_URL = "sqlite:///./payments.db"

engine=create_engine(DATABASE_URL)

sessionlocal=sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)
base=declarative_base()