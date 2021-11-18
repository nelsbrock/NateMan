# NateMan – Nachschreibtermin-Manager
# __init__.py
# Copyright © 2020  Niklas Elsbrock
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Enthält die Initialisierungsfunktion der NateMan-Webapp.
"""

import locale
import logging.handlers
import os
import sys
from datetime import datetime

import sqlalchemy
from flask import Flask
from flask.logging import default_handler

from . import util
from .config_manager import config_file_exists, create_config_file, config
from .config_manager import read_config_file
from .models import Klausur, Klausurteilnahme, Lehrer, Schueler, Stufe, db


def create_app() -> Flask:
    """Initialisiert die NateMan-Webapp"""

    app: Flask = Flask(__name__, instance_relative_config=True)

    # Sprache festlegen
    locale.setlocale(locale.LC_ALL, "")

    setup_logging(app)

    # falls nötig, instance-Ordner anlegen
    os.makedirs(app.instance_path, exist_ok=True)

    load_config(app)

    secret_key = read_or_generate_secret_key(app)

    configure_jinja(app)

    # Falls in der Konfiguration aktiviert, Datei-Logging einrichten
    if config["logging"].get("syslog", False):
        setup_syslog(app)

    # Logging-Level ändern
    app.logger.setLevel(config["logging"]["level"])

    # Flask und Flask-SQLAlchemy konfigurieren
    app.config.from_mapping(
        SERVER_NAME=config["server-name"],
        SECRET_KEY=secret_key,
        PREFERRED_URL_SCHEME="https" if config["uses-ssl"] else "http",
        SESSION_COOKIE_SECURE=config["uses-ssl"],
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16 MiB upload limit
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "nateman.sqlite3"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    db.init_app(app)
    db.create_all(app=app)

    with app.app_context():
        init_db(app)

    # Blueprints registrieren
    register_blueprints(app)

    return app


def setup_logging(app: Flask):
    stdout_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="[%(asctime)s | %(levelname)s]: %(message)s"
    )
    stdout_handler.setFormatter(formatter)
    app.logger.removeHandler(default_handler)
    app.logger.addHandler(stdout_handler)


def load_config(app: Flask):
    """
    Liest die Konfigurationsdatei.
    Falls keine vorhanden ist, wird vorher eine erstellt.
    """
    if not config_file_exists(app):
        config_path = create_config_file(app)
        app.logger.info(f"Da die Konfigurationsdatei nicht gefunden werden konnte, "
                        f"wurde eine neue erstellt ({config_path}).")

    # Konfigurationsdatei laden
    read_config_file(app)


def read_or_generate_secret_key(app: Flask) -> bytes:
    """ Liest den Secret Key aus bzw. generiert ihn, falls noch keiner vorhanden ist. """
    secret_key_path = os.path.join(app.instance_path, "SECRET_KEY")

    if not os.path.isfile(secret_key_path):
        with open(os.open(secret_key_path, os.O_WRONLY | os.O_CREAT, mode=0o600), "wb") as file:
            secret_key = os.urandom(128)
            file.write(secret_key)
    else:
        with open(secret_key_path, "rb") as file:
            secret_key = file.read()

    return secret_key


def configure_jinja(app: Flask):
    app.jinja_env.globals.update(
        nateman_config=config,
        util=util,
        sqlalchemy=sqlalchemy,
        datetime=datetime,
        db=db,
        Klausurteilnahme=Klausurteilnahme,
        Stufe=Stufe,
        Schueler=Schueler,
        Lehrer=Lehrer,
        Klausur=Klausur
    )
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.strip_trailing_newlines = False


def setup_syslog(app: Flask):
    """ Erstellt Logging-Handler zum loggen in Syslog. """
    file_handler = logging.handlers.SysLogHandler(address="/dev/log")
    file_formatter = logging.Formatter(fmt="nateman: [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)
    app.logger.addHandler(file_handler)


def init_db(app: Flask):
    """ Initialisiert Stufen und Administratorkonto, falls nicht vorhanden """
    if Stufe.query.count() == 0:
        new_stufen_namen = ["EF", "Q1", "Q2"]
        for stufe_name in new_stufen_namen:
            stufe = Stufe(name=stufe_name)
            db.session.add(stufe)
        app.logger.info(f"Da keine Stufen vorhanden waren, wurden neue erstellt ({', '.join(new_stufen_namen)}).")

    if Lehrer.query.count() == 0:
        new_lehrer_kuerzel = "admin"
        new_lehrer_password = "admin"
        lehrer = Lehrer(kuerzel=new_lehrer_kuerzel, is_admin=True, pwd_changed=False)
        lehrer.set_password(new_lehrer_password, set_pwd_changed=False)
        db.session.add(lehrer)
        app.logger.info(f"Da keine Lehrerkonten vorhanden waren, wurde ein neues Administratorkonto erstellt. "
                        f"(Kürzel: {new_lehrer_kuerzel}; Passwort: {new_lehrer_password})")

    db.session.commit()


def register_blueprints(app: Flask):
    """ Registriert die Flask-Blueprints """
    from . import blueprints
    from .blueprints import admin, auth, error, fileio, info, klausuren, schueler
    from .blueprints.admin import lehrer as admin_lehrer
    app.register_blueprint(blueprints.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(admin_lehrer.bp, name="admin.lehrer")
    app.register_blueprint(auth.bp)
    app.register_blueprint(error.bp)
    app.register_blueprint(fileio.bp)
    app.register_blueprint(info.bp)
    app.register_blueprint(klausuren.bp)
    app.register_blueprint(schueler.bp)
