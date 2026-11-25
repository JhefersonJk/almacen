"""Motor independiente de Gráfica Ali; las tablas de pedidos originales no se tocan."""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parents[1]


class Base(DeclarativeBase):
    pass


def configure(database_url: str | None = None):
    url = database_url or os.getenv('ALMACEN_DATABASE_URL')
    if not url:
        directory = ROOT / 'data'
        directory.mkdir(parents=True, exist_ok=True)
        url = f'sqlite:///{directory / "almacen.db"}'
    parsed = make_url(url)
    if parsed.get_backend_name() != 'sqlite':
        raise ValueError('Esta versión usa SQLite; configura ALMACEN_DATABASE_URL=sqlite:///...')
    if parsed.database and parsed.database != ':memory:' and not parsed.query.get('uri'):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={'check_same_thread': False, 'timeout': 15})

    @event.listens_for(engine, 'connect')
    def sqlite_integrity(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=15000')

    return engine, sessionmaker(bind=engine, expire_on_commit=False)
