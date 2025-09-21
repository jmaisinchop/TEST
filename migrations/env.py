# migrations/env.py

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
# Importa tus modelos para que Alembic los reconozca
from app.models import *

flask_app = create_app()
target_metadata = db.metadata

# Lista de las tablas que TU APP debe gestionar
MY_APP_TABLES = {
    'carteras', 'grupos', 'grupo_empleados', 'justificaciones',
    'grupo_horarios_especiales', 'department_horarios_especiales',
    'allowed_ips','permisos', 'alembic_version'
}

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name not in MY_APP_TABLES:
        return False
    else:
        return True

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline() -> None:
    context.configure(
        url=flask_app.config['SQLALCHEMY_DATABASE_URI'],
        target_metadata=target_metadata, literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object, compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = flask_app.config['SQLALCHEMY_DATABASE_URI']
    connectable = engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            include_object=include_object, compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()