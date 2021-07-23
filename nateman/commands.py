# NateMan – Nachschreibtermin-Manager
# commands.py
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
Enthält Befehle zur Verwendung im Terminal (Command Line Interface).
"""

import click
from flask.cli import with_appcontext

from nateman.exporter import excelexport
from nateman.importer import excelimport, KoopSchuelerImportError
from . import emails, util, assigner
from .models import Koopschule, Lehrer, Stufe, db, Session
from .config_manager import config


@click.group()
def cli():
    """Enthält Befehle zur Steuerung der NateMan-Webanwendung."""
    pass


@click.command("add-lehrer")
@click.argument("kuerzel", type=click.STRING)
@click.option("--password", type=click.STRING, default=None)
@click.option("--admin", is_flag=True)
@with_appcontext
def add_lehrer_command(kuerzel, password, admin):
    """Erstellt einen Lehreraccount."""

    lehrer = Lehrer.query.filter_by(kuerzel=kuerzel).first()

    if lehrer is not None:
        click.echo("Fehler: Ein(e) Lehrer(in) mit diesem Kürzel ist bereits registriert.", err=True)
        return 1

    if not password:
        password = click.prompt("Neues Passwort eingeben (unsichtbar)", hide_input=True)

    if not util.validate_bcrypt_password(password):
        click.echo("Fehler: Das Passwort darf höchstens 72 Bytes groß sein.", err=True)
        return 1

    new_lehrer = Lehrer(kuerzel=kuerzel, is_admin=admin)
    new_lehrer.set_password(password)
    db.session.add(new_lehrer)
    db.session.commit()

    click.echo("Lehrer(in) wurde erfolgreich registriert.")
    return 0


@click.command("add-stufe")
@click.argument("names", type=click.STRING, nargs=-1)
@with_appcontext
def add_stufe_command(names):
    """Fügt eine neue Stufe zur Datenbank hinzu."""

    if len(names) == 0:
        click.echo("Fehler: Bitte geben Sie mindestens eine Stufe an.", err=True)
        return 1

    for name in names:
        if util.is_integer_string(name):
            click.echo(f"Fehler: Stufenname darf keine Ganzzahl sein.", err=True)
            return 1

        stufe = Stufe.query.filter_by(name=name).first()

        if stufe is not None:
            click.echo(f"Fehler: Die Stufe {name} existiert bereits.", err=True)
            return 1

        new_stufe = Stufe(name=name)
        db.session.add(new_stufe)

    db.session.commit()

    click.echo("Die Stufe(n) wurde(n) erfolgreich hinzugefügt.")
    return 0


@click.command("remove-stufe")
@click.argument("name", type=click.STRING)
@click.option("--yes", is_flag=True)
@with_appcontext
def remove_stufe_command(name, yes):
    """Entfernt eine Stufe und alle mit ihr verknüpften Daten von der Datenbank."""

    stufe = Stufe.query.filter_by(name=name).first()

    if stufe is None:
        click.echo("Fehler: Diese Stufe existiert nicht.", err=True)
        return 1

    if not yes:
        if not click.confirm(f"Durch diesen Vorgang werden alle mit der Stufe {stufe.name} verknüpften Daten gelöscht. "
                             f"Fortfahren?"):
            click.echo("Vorgang abgebrochen.")
            return 0

    db.session.delete(stufe)
    db.session.commit()

    click.echo("Die Stufe wurde erfolgreich entfernt.")
    return 0


@click.command("add-koopschule")
@click.argument("kuerzel", type=click.STRING)
@click.argument("name", type=click.STRING)
@with_appcontext
def add_koopschule_command(kuerzel, name):
    """Fügt eine Koop-Schule zur Datenbank hinzu."""
    koop_schule = Koopschule.query.filter_by(name=name).first()

    if koop_schule is not None:
        click.echo(f"Fehler: Eine Koop-Schule mit dem Kürzel {kuerzel} existiert bereits.", err=True)
        return 1

    new_koop_schule = Koopschule(kuerzel=kuerzel, name=name)
    db.session.add(new_koop_schule)

    db.session.commit()

    click.echo("Die Koop-Schule wurde erfolgreich hinzugefügt.")
    return 0


@click.command("remove-koopschule")
@click.argument("kuerzel", type=click.STRING)
@with_appcontext
def remove_koopschule_command(kuerzel):
    """Entfernt eine Koop-Schule und alle mit ihr verknüpften Daten von der Datenbank."""

    koop_schule = Koopschule.query.filter_by(kuerzel=kuerzel).first()

    if koop_schule is None:
        click.echo(f"Fehler: Eine Koop-Schule mit dem Kürzel {kuerzel} existiert nicht.", err=True)
        return 1

    db.session.delete(koop_schule)
    db.session.commit()

    click.echo("Die Koop-Schule wurde erfolgreich entfernt.")
    return 0


@click.command("make-admin")
@click.argument("kuerzel")
@with_appcontext
def make_admin_command(kuerzel):
    """Gibt einem/einer Lehrer(in) Administratorrechte."""

    lehrer = Lehrer.query.filter_by(kuerzel=kuerzel).first()

    if lehrer is None:
        click.echo("Fehler: Das angegebene Kürzel ist nicht registriert.", err=True)
        return 1

    if lehrer.is_admin:
        click.echo(kuerzel + " ist bereits Administrator.")
        return 0

    lehrer.is_admin = True
    db.session.commit()
    click.echo(kuerzel + " ist jetzt Administrator.")
    return 0


@click.command("take-admin")
@click.argument("kuerzel")
@with_appcontext
def take_admin_command(kuerzel):
    """Nimmt einem/einer Lehrer(in) seine/ihre Administratorrechte."""

    lehrer = Lehrer.query.filter_by(kuerzel=kuerzel).first()

    if lehrer is None:
        click.echo("Fehler: Das angegebene Kürzel ist nicht registriert.", err=True)
        return 1

    if not lehrer.is_admin:
        click.echo(kuerzel + " ist bereits kein Administrator.")
        return 0

    lehrer.is_admin = False
    db.session.commit()
    click.echo(kuerzel + " ist jetzt kein Administrator mehr.")
    return 0


@click.command("cleanup")
@with_appcontext
def cleanup_command():
    """Entfernt abgelaufene Daten aus der NateMan-Datenbank."""
    Session.cleanup()
    Lehrer.password_reset_cleanup()
    db.session.commit()
    return 0


@click.command("send-reminder-mails")
@with_appcontext
def send_reminder_mails_command():
    """Sendet Erinnerungsemails an alle Lehrer(innen), die unbearbeitete vergangene Klausuren haben."""
    emails.send_reminder_mails()
    return 0


@click.command("apply-email-format")
@click.option("-f", "--format", "fmt", type=click.STRING, default=None)
@click.option("-o", "--override", is_flag=True)
@with_appcontext
def apply_email_format_command(fmt, override):
    """Wendet das E-Mail-Adressen-Format auf Lehrer an."""
    fmt = fmt or config.get("email-address-format", None)
    if fmt is None:
        click.echo("Fehler: Ein Format ist weder konfiguriert, noch wurde eines angegeben.", err=True)
        return 1

    query = Lehrer.query if override else Lehrer.query.filter_by(email=None)
    lehrer = query.all()
    for l in lehrer:
        l.set_default_email_address(fmt)

    db.session.commit()

    return 0


def init_commands():
    cli.add_command(add_lehrer_command)
    cli.add_command(make_admin_command)
    cli.add_command(take_admin_command)
    cli.add_command(add_stufe_command)
    cli.add_command(remove_stufe_command)
    cli.add_command(add_koopschule_command)
    cli.add_command(remove_koopschule_command)
    cli.add_command(send_reminder_mails_command)
    cli.add_command(apply_email_format_command)
    cli.add_command(cleanup_command)


init_commands()
