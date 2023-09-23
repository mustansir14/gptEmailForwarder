from sqlalchemy import create_engine
from sqlalchemy import JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
import os
from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv()


class Base(DeclarativeBase):
    pass


class Config(Base):
    __tablename__ = "config"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_json = mapped_column(JSON)


engine = create_engine(os.getenv("DATABASE_URL"))
Session = sessionmaker(bind=engine)

Base.metadata.create_all(engine)


def get_config() -> Config:
    with Session() as session:
        return session.scalar(select(Config))


def update_or_create_config(config_json: dict) -> Config:
    config = get_config()
    if config:
        config.config_json = config_json
    else:
        config = Config(config_json=config_json)
    with Session() as session:
        session.add(config)
        session.commit()
