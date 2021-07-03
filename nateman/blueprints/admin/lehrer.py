# NateMan – Nachschreibtermin-Manager
# blueprints/admin/lehrer.py
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
Lehrerkonten-Administrations-Blueprint
"""

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from ..auth import admin_required
from ... import util
from ...models import Lehrer, Stufe, db

bp = Blueprint("lehrer", __name__, url_prefix="/admin/lehrer")


@bp.route("/")
@admin_required
def index():
    """ Lehrerliste """
    return render_template("admin/lehrer/index.html.j2")


@bp.route("/<int:lehrer_id>", methods=("GET", "POST"))
@admin_required
def edit(lehrer_id):
    """ Lehrerbearbeitung """
    lehrer: Lehrer = Lehrer.query.filter_by(id=lehrer_id).first()

    # HTTP 404 Fehler erzeugen, wenn kein Lehrer unter der ID gefunden wurde
    if not lehrer:
        abort(404)
        return

    if request.method != "POST":
        return render_template("admin/lehrer/edit.html.j2", lehrer=lehrer)

    # ELSE

    action = request.form["action"]

    # Benutzerdaten ändern
    if action == "change-credentials":
        new_kuerzel = request.form["new-kuerzel"].strip()
        new_email = request.form["new-email"].strip() or None
        new_password = request.form["new-password"]

        new_beraet_name = request.form["new-beraet"]

        new_is_admin = ("new-admin" in request.form)

        error_msg = None

        change_kuerzel = False
        change_email = False
        change_password = False
        change_beraet = False
        change_is_admin = False

        # Neues Kürzel, falls angegeben und nicht das aktuelle Kürzel
        if new_kuerzel and new_kuerzel != lehrer.kuerzel:
            change_kuerzel = True
            # existiert das Kürzel bereits?
            if Lehrer.query.filter_by(kuerzel=new_kuerzel).count() != 0:
                error_msg = "Das angegebene Kürzel ist bereits registriert."

        # Neue E-Mail-Adresse, falls angegeben und nicht die aktuelle Adresse
        if new_email != lehrer.email:
            change_email = True
            # ist die neue E-Mail-Adresse syntaktisch ungültig?
            if new_email is not None and not util.EMAIL_ADDRESS_REGEX.match(new_email):
                error_msg = "Bitte geben Sie eine gültige E-Mail-Adresse ein."

        # Neues Passwort, falls angegeben
        if new_password:
            change_password = True
            # ist das neue Passwort zu groß?
            if not util.validate_bcrypt_password(new_password):
                error_msg = "Das neue Passwort darf höchstens 72 Zeichen lang sein."

        if new_beraet_name == "":
            new_beraet = None
        else:
            new_beraet = Stufe.query.filter_by(name=new_beraet_name).first()
            if new_beraet is None:
                abort(400)
                return

        if new_beraet != lehrer.beraet:
            change_beraet = True

        # Administratorstatus ändern
        if new_is_admin != lehrer.is_admin:
            change_is_admin = True

        # Änderungen vornehmen, falls kein Fehler aufgetreten ist
        if error_msg is not None:
            # Es ist ein Fehler aufgetreten
            flash(error_msg, "error")
            return redirect(url_for(".edit", lehrer_id=lehrer_id), code=303)

        if not (change_kuerzel or change_email or change_password or change_beraet or change_is_admin):
            flash("Es wurde nichts geändert.", "error")
            return redirect(url_for(".edit", lehrer_id=lehrer_id), code=303)

        if change_kuerzel:
            old_kuerzel = lehrer.kuerzel
            lehrer.kuerzel = new_kuerzel
            current_app.logger.info(f"{g.lehrer} hat das Lehrerkürzel des Kontos mit der ID {lehrer.id}"
                                    f" von {old_kuerzel} auf {new_kuerzel} geändert.")

        if change_email:
            # E-Mail-Adresse wird als confirmed markiert, wenn ein Admin sie ändert
            lehrer.email = new_email
            lehrer.confirmation_token = None
            lehrer.is_confirmed = True
            current_app.logger.info(f"{g.lehrer} hat die E-Mail-Adresse von {lehrer} auf {new_email} gesetzt.")

        if change_password:
            lehrer.set_password(new_password)
            current_app.logger.info(f"{g.lehrer} hat das Passwort von {lehrer} geändert.")

        if change_beraet:
            lehrer.beraet = new_beraet
            if new_beraet:
                current_app.logger.info(f"{g.lehrer} hat {lehrer} als Beratungslehrer(in) für die {new_beraet.name} "
                                        f"festgelegt.")
            else:
                current_app.logger.info(f"{g.lehrer} hat den Beratungslehrerstatus von {lehrer} entfernt.")

        if change_is_admin:
            lehrer.is_admin = new_is_admin
            if new_is_admin:
                current_app.logger.info(f"{g.lehrer} hat {lehrer} den Administratorstatus vergeben.")
            else:
                current_app.logger.info(f"{g.lehrer} hat {lehrer} den Administratorstatus entfernt.")

        db.session.commit()
        flash("Benutzerdaten erfolgreich geändert.", "success")
        return redirect(url_for(".edit", lehrer_id=lehrer_id), code=303)

    # Account löschen
    elif action == "delete-account":
        current_app.logger.info(f"{g.lehrer} hat das Konto {lehrer} gelöscht.")

        db.session.delete(lehrer)
        db.session.commit()
        flash("Benutzerkonto erfolgreich gelöscht.", "success")

        return redirect(url_for(".index"), code=303)

    abort(400)  # Bad Request, wenn ungültige action


@bp.route("/add", methods=("GET", "POST"))
@admin_required
def add():
    """ Lehrerhinzufügung """
    if request.method != "POST":
        return render_template("admin/lehrer/add.html.j2")

    # ELSE

    kuerzel = request.form["kuerzel"]
    password = request.form["password"]
    force_pwd_change = ("force-password-change" in request.form)

    error_msg = None

    # existiert das Kürzel bereits?
    if Lehrer.query.filter_by(kuerzel=kuerzel).count() != 0:
        error_msg = "Ein(e) Lehrer(in) mit diesem Kürzel existiert bereits."

    # ist das neue Passwort zu groß?
    elif not util.validate_bcrypt_password(password):
        error_msg = "Das neue Passwort darf höchstens 72 Zeichen lang sein."

    if error_msg:
        flash(error_msg, "error")
        return redirect(url_for(".add"), code=303)

    new_lehrer = Lehrer(kuerzel=kuerzel)

    new_lehrer.set_password(password, set_pwd_changed=not force_pwd_change)

    db.session.add(new_lehrer)
    db.session.commit()

    flash("Lehrer(in) erfolgreich hinzugefügt.", "success")
    current_app.logger.info(f"{g.lehrer} hat den/die Lehrer(in) {new_lehrer} hinzugefügt")

    return redirect(url_for(".edit", lehrer_id=new_lehrer.id), code=303)
