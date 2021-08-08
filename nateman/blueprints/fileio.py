# NateMan – Nachschreibtermin-Manager
# blueprints/fileio.py
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
Export- und Import-Blueprint
"""
import os
import tempfile
from datetime import datetime

from flask import abort, Blueprint, current_app, g, redirect, url_for, flash, request, render_template
from openpyxl.utils.exceptions import InvalidFileException
from pyexpat import ExpatError

from .auth import beratungslehrer_required, admin_required
from .. import exporter, util
from ..importer import KlausurplanImportError, import_plan, excelimport, KoopSchuelerImportError
from ..models import db, Stufe, Klausur, Schueler

bp = Blueprint("fileio", __name__)


@bp.route("/export")
@beratungslehrer_required
def export():
    """ Export (Seite *Nachschreibplan exportieren*)"""
    with tempfile.NamedTemporaryFile(prefix="nateman_export_") as fp:
        exporter.excelexport(fp.name, g.lehrer.accessible_stufen())
        # XLSX-Datei wird in ``filebytes`` geladen, damit die temporäre Datei gelöscht werden kann
        fp.seek(0)
        filebytes = fp.read()

    download_name = "NateMan-Export " + datetime.now().strftime("%Y-%m-%d") + ".xlsx"
    xlsx_mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response = current_app.response_class(filebytes, mimetype=xlsx_mimetype)
    response.headers.set("Content-Disposition", "attachment", filename=download_name)

    return response


@bp.route("/import", methods=("GET", "POST"), endpoint="import")
@admin_required
def import_():
    """ Import (Seite *Klausurpläne importieren*) """
    if request.method != "POST":
        return render_template("fileio/import.html.j2")

    # ELSE

    all_stufen = Stufe.query.all()

    for stufe in all_stufen:
        if "del_" + stufe.name in request.form:
            if not g.lehrer.can_access(stufe):
                abort(400)
                return

            _del_plan(stufe)
            db.session.commit()

            flash("Klausurplan erfolgreich gelöscht.", "success")
            current_app.logger.info(f"{g.lehrer} hat den Klausurplan für die {stufe.name} gelöscht.")
            return redirect(url_for(".import"), code=303)

    new_lehrer_password = request.form["new-lehrer-password"]

    error_msg = None
    if not new_lehrer_password:
        error_msg = "Bitte geben Sie das Passwort für neu registrierte Lehrerkonten an."
    elif not util.validate_bcrypt_password(new_lehrer_password):
        error_msg = "Das Passwort für neue Lehrerkonten darf nicht mehr als 72 Zeichen enthalten."
    if error_msg is not None:
        flash(error_msg, "error")
        return redirect(url_for(".import"), code=303)

    plan_given = []

    for stufe in all_stufen:
        plan = request.files.get("plan_" + stufe.name, None)

        # Klausurplan importieren
        if plan and plan.filename:
            plan_given.append(stufe.name)

            _del_plan(stufe)

            try:
                import_plan(plan, stufe, new_lehrer_password)
            except (KeyError, ValueError, ExpatError, KlausurplanImportError) as exc:
                db.session.rollback()

                flash(f"Beim Importieren des Klausurplans für die {stufe.name} ist ein Fehler aufgetreten.\n"
                      f"Wahrscheinlich ist die Klausurplandatei ungültig oder es gibt einen Konflikt mit den "
                      f"bisherigen Daten.\n\nFehlerbeschreibung: {type(exc).__name__}\n{exc}", "error")

                current_app.logger.warning(f"Beim Versuch von {g.lehrer}, einen Klausurplan zu importieren, "
                                           f"ist ein Fehler aufgetreten.", exc_info=exc)
                return redirect(url_for(".import"), code=303)

    ks_file = request.files.get("koopschueler", None)
    ks_file_given = False

    # Koopschülerdatei importieren
    ks_import_failures = []
    if ks_file and ks_file.filename:
        ks_file_given = True
        _del_koopschueler()

        filename_ext = os.path.splitext(ks_file.filename)[1]
        with tempfile.NamedTemporaryFile(prefix="nateman_ks_import_", suffix=filename_ext) as fp:
            ks_file.save(fp.name)

            try:
                ks_import_failures = excelimport(fp.name)
            except (InvalidFileException, KoopSchuelerImportError) as exc:
                db.session.rollback()

                flash(f"Beim Importieren der Koopschülerliste ist ein Fehler aufgetreten.\n\n"
                      f"Fehlerbeschreibung: {type(exc).__name__}\n{exc}", "error")

                current_app.logger.warning(f"Beim Versuch von {g.lehrer}, eine Koopschülerliste zu importieren, "
                                           f"ist ein Fehler aufgetreten.", exc_info=exc)
            return redirect(url_for(".import"), code=303)

    if len(plan_given) == 0 and not ks_file_given:
        flash("Es wurden keine Pläne angegeben.", "error")
    else:
        if len(ks_import_failures) == 0:
            flash("Pläne importiert.", "success")
        else:
            flash("Pläne importiert.\n\nKoopschülerimport: Folgende SuS konnten nicht importiert werden:\n"
                  + "; ".join(f"{failure[0]}, {failure[1]}" for failure in ks_import_failures) + ".\n"
                  "Die restlichen KoopSuS wurden trotzdem importiert.", "warning")
        current_app.logger.info(f"{g.lehrer} hat Pläne importiert.")
        db.session.commit()

    return redirect(url_for(".import"), code=303)


def _del_plan(stufe: Stufe):
    """Löscht alle Klausuren und Schüler der angegebenen Stufe"""
    stufe.import_date = None
    Klausur.query.filter_by(stufe=stufe).delete()
    Schueler.query.filter_by(stufe=stufe).delete()


def _del_koopschueler():
    """Löscht alle Koopschüler"""
    Schueler.query.filter(Schueler.koop).delete()
