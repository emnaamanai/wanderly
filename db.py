import sqlite3
import click
from flask import g, current_app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect("wanderly.db")
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))


@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Base de données créée.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)