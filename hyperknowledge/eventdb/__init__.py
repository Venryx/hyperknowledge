from asyncio import current_task
from datetime import datetime
from threading import current_thread
from uuid import UUID

from pydantic import AnyUrl, constr
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.ext.asyncio import async_scoped_session, async_sessionmaker, create_async_engine
from sqlalchemy.util import ScopedRegistry
from sqlalchemy import event

from .pydantic_adapters import PydanticURIRef
from .. import target_db, engine_url

Name = constr(pattern=r'\w+')
QName = constr(pattern=r'\w+:\w+')

StreamId = PydanticURIRef
Timestamp = datetime
EntityId = UUID
SchemaId = PydanticURIRef
SchemaName = Name
SchemaElementFull = PydanticURIRef
SchemaElement = QName
UserId = Name
dbTopicId = BIGINT

def as_tuple(val):
    if isinstance(val, (tuple, list)):
        return tuple(val)
    return (val,)

def as_tuple_or_scalar(val):
    if isinstance(val, (tuple, list)):
        return tuple(val)
    return val

def make_engine(db=target_db, owner=True):
    # cf https://github.com/MagicStack/asyncpg/issues/530
    engine = create_async_engine(engine_url(db, owner), connect_args={'server_settings': {'jit': 'off'}})
    # The following should make the jit setting unnecessary but does not.
    # Still does not hurt, and keeping for reference
    from .models import all_enums

    @event.listens_for(engine.sync_engine, "connect")
    def connect(conn, connection_record):
        for enum_name in [e.name for e in all_enums]:
            conn.driver_connection.set_builtin_type_codec(enum_name, schema='public', codec_name="text")
    return engine

def make_session_factory(owner=True):
    return async_sessionmaker(make_engine(owner=owner), expire_on_commit=False)

# We need an engine per thread, see https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-multiple-asyncio-event-loops
owner_session_factory_registry = ScopedRegistry(make_session_factory, current_thread)
client_session_factory_registry = ScopedRegistry(lambda: make_session_factory(owner=False), current_thread)


owner_scoped_session = async_scoped_session(lambda: owner_session_factory_registry()(), scopefunc=current_task)
client_scoped_session = async_scoped_session(lambda: client_session_factory_registry()(), scopefunc=current_task)
