# NateMan – Nachschreibtermin-Manager
# models.py
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
Enthält die SQLAlchemy-Modelle.
"""
from datetime import datetime, timedelta
from sqlite3 import Connection as Sqlite3_Connection
from typing import Optional, Tuple, Union, AnyStr

import bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from sqlalchemy.engine import Engine
from sqlalchemy.sql import func

from . import util

db: SQLAlchemy = SQLAlchemy()


class Klausurteilnahme(db.Model):
    klausur_id = db.Column(db.Integer, db.ForeignKey("klausur.id", onupdate="CASCADE", ondelete="CASCADE"),
                           primary_key=True)
    schueler_id = db.Column(db.Integer, db.ForeignKey("schueler.id", onupdate="CASCADE", ondelete="CASCADE"),
                            primary_key=True)
    versaeumt = db.Column(db.Boolean, default=False, nullable=False)
    attestiert = db.Column(db.Boolean, default=False, nullable=False)
    nachgeschrieben = db.Column(db.Boolean, default=False, nullable=False)

    klausur = db.relationship("Klausur", lazy="joined")
    schueler = db.relationship("Schueler", lazy="joined")


class Stufe(db.Model):
    name = db.Column(db.String(), primary_key=True)
    import_date = db.Column(db.Date(), default=None)


class Schueler(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nachname = db.Column(db.String(collation="NOCASE"), nullable=False)
    vorname = db.Column(db.String(collation="NOCASE"), nullable=False)
    stufe_name = db.Column(db.String(), db.ForeignKey("stufe.name", onupdate="CASCADE", ondelete="CASCADE"),
                           nullable=False)
    koop = db.Column(db.Boolean, default=False, nullable=False)

    stufe = db.relationship("Stufe", lazy="select")

    def __str__(self):
        return f"{self.nachname}, {self.vorname} ({self.stufe.name}, ID:{self.id})"


class Lehrer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kuerzel = db.Column(db.String(collation="NOCASE"), unique=True, nullable=False)
    email = db.Column(db.String())
    is_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    pwd_hash = db.Column(db.String(), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    beraet_name = db.Column(db.String(), db.ForeignKey("stufe.name", onupdate="CASCADE", ondelete="SET NULL"))
    pwd_changed = db.Column(db.Boolean, default=False, nullable=False)
    confirmation_token = db.Column(db.String(), unique=True)
    password_reset_token = db.Column(db.String(), unique=True)
    password_reset_expiry = db.Column(db.DateTime)

    beraet = db.relationship("Stufe", lazy="select")

    @staticmethod
    def password_reset_cleanup() -> None:
        """
        Entfernt alle abgelaufenen Passwortzurücksetzungsanfragen aus der Datenbank.
        """
        Lehrer.query.filter(Lehrer.password_reset_expiry < datetime.utcnow()) \
            .update({Lehrer.password_reset_token: None, Lehrer.password_reset_expiry: None})

    def __str__(self):
        return f"{self.kuerzel} (ID:{self.id})"

    def can_access(self, stufe: Optional[Stufe] = None) -> bool:
        """
        Überprüft, ob dieser Lehrer erweiterten Zugriff auf die angegebene Stufe hat
        (d.h. ob er Administrator oder Beratungslehrer der angegebenen Stufe ist).

        Wenn die Stufe ``None`` ist, wird überprüft, ob dieser Lehrer
        Administrator oder Beratungslehrer irgendeiner Stufe ist.

        :return: ``True`` falls ja, ``False`` falls nicht
        """
        if self.is_admin:
            return True
        # ELSE
        if stufe is None:
            return self.beraet is not None
        # ELSE
        return self.beraet == stufe

    def accessible_stufen(self, names: bool = False) -> Union[Tuple[Stufe, ...], Tuple[AnyStr, ...]]:
        """
        :param names: Falls ``True``, werden die Namen der Stufen anstelle der Stufenobjekte zurückgegeben
        :return: Tupel mit allen Stufen, auf die dieser Lehrer erweiterten Zugriff hat
        """
        stufen = Stufe.query.all()
        if self.is_admin:
            return tuple(stufen) if not names else tuple(s.name for s in stufen)
        # ELSE
        if self.beraet:
            return (self.beraet,) if not names else (self.beraet.name,)
        # ELSE
        return ()

    def set_password(self, new_password: str, set_pwd_changed=True) -> None:
        """
        Legt das neue Passwort des Lehrers fest.

        :param new_password: neues Passwort
        :param set_pwd_changed: legt fest, ob der ``pwd_changed``-Eintrag in der Datenbank angepasst werden soll
        """
        assert util.validate_bcrypt_password(new_password)
        self.pwd_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        if set_pwd_changed:
            self.pwd_changed = True

    def check_password(self, password) -> bool:
        """
        Vergleicht ``password`` mit dem Passwort des Lehrers.

        :param password: zu überprüfendes Passwort
        :return: ``True`` falls die Passwörter übereinstimmen, ``False`` falls nicht
        """
        return bcrypt.checkpw(password.encode("utf-8"), self.pwd_hash)

    def set_default_email_address(self, fmt) -> bool:
        email_address = fmt.replace("?", util.email_address_safe(self.kuerzel))
        if util.EMAIL_ADDRESS_REGEX.match(email_address):
            self.email = email_address
            self.is_confirmed = True
            return True

        return False


class Klausur(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kursname = db.Column(db.String(collation="NOCASE"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    startperiod = db.Column(db.Integer, nullable=False)
    endperiod = db.Column(db.Integer, nullable=False)
    laenge = db.Column(db.Integer, default=None)
    edited = db.Column(db.Boolean, default=False, nullable=False)
    annotation = db.Column(db.String())
    stufe_name = db.Column(db.String(), db.ForeignKey("stufe.name", onupdate="CASCADE", ondelete="CASCADE"),
                           nullable=False)
    lehrer_id = db.Column(db.Integer, db.ForeignKey("lehrer.id", onupdate="CASCADE", ondelete="CASCADE"),
                          nullable=False)

    stufe = db.relationship("Stufe", lazy="select")
    lehrer = db.relationship("Lehrer", lazy="joined")

    __table_args__ = (
        CheckConstraint("startperiod >= 0"),
        CheckConstraint("startperiod <= endperiod")
    )

    def __str__(self):
        return f"{self.kursname}, {self.stufe.name} (ID:{self.id})"

    def is_bygone(self):
        """
        :return: ``True``, falls diese Klausur vergangen ist, ``False``, falls nicht
        """
        return self.date <= datetime.now().date()


class Session(db.Model):
    key = db.Column(db.String(), primary_key=True)
    expiry = db.Column(db.DateTime, nullable=False)
    lehrer_id = db.Column(db.Integer, db.ForeignKey("lehrer.id", onupdate="CASCADE", ondelete="CASCADE"),
                          nullable=False)

    lehrer = db.relationship("Lehrer", lazy="joined")

    @staticmethod
    def get(key: str) -> Optional["Session"]:
        """
        Gibt die Sitzung zurück, die zum Key gehört oder ``None``,
        falls keine Sitzung mit dem Key existiert oder die Sitzung abgelaufen ist.

        :param key: Sitzungs-Key
        :return: Sitzung
        """
        session = Session.query.filter_by(key=key).first()
        if session is not None and session.expired():
            return None

        return session

    @staticmethod
    def create(lehrer: Lehrer, expiry_delta: timedelta) -> "Session":
        """
        Erstellt eine neue Sitzung für den Lehrer ``lehrer``.

        :param lehrer: Lehrer, für den eine Sitzung erstellt werden soll
        :param expiry_delta: Zeitraum, nach dem die Sitzung ablaufen soll
        :return: neue Sitzung
        """
        new_session = Session(key=util.random_uri_safe_string(64), expiry=datetime.utcnow() + expiry_delta,
                              lehrer=lehrer)
        db.session.add(new_session)
        return new_session

    @staticmethod
    def cleanup() -> None:
        """
        Entfernt alle abgelaufenen Sitzungen aus der Datenbank.
        """
        Session.query.filter(Session.expiry < datetime.utcnow()).delete()

    def expired(self) -> bool:
        """
        Überprüft, ob die Sitzung abgelaufen ist.
        """
        return self.expiry < datetime.utcnow()


@db.event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Falls SQLite verwendet wird, wird bei jedem Verbindungsaufbau zur Datenbank ``foreign_keys`` aktiviert, damit
    Fremdschlüssel richtig funktionieren.
    Von https://stackoverflow.com/questions/4477269.
    """
    if type(dbapi_connection) is Sqlite3_Connection:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_next_new_schueler_id():
    """
    :return: ID, die der nächste manuell hinzugefügte Schüler haben soll
    """
    lowest_id = db.session.query(func.min(Schueler.id).label("min_id")).one().min_id
    if lowest_id is None or lowest_id > -1:
        return -1
    # ELSE
    return lowest_id - 1
