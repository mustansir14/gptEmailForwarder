import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from internal.models import Base, Config

load_dotenv()


db_url = os.getenv("DATABASE_URL")
db_url = db_url.replace("postgres://", "postgresql+psycopg2://")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)

Base.metadata.create_all(engine)


def get_config_from_db() -> Config:
    with Session() as session:
        return session.scalar(select(Config))


def update_or_create_config(config_json: dict) -> Config:
    config = get_config_from_db()
    if config:
        config.config_json = config_json
    else:
        config = Config(config_json=config_json)
    with Session() as session:
        session.add(config)
        session.commit()
