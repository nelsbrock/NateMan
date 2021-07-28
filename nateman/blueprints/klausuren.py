# NateMan – Nachschreibtermin-Manager
# blueprints/klausuren.py
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
Klausurlisten-Blueprint
"""

from datetime import datetime

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for, Response

from .auth import login_required, beratungslehrer_required
from ..config_manager import config
from ..models import Klausur, Klausurteilnahme, Koopschule, Lehrer, Schueler, db, \
    get_next_new_schueler_id, Stufe

bp = Blueprint("klausuren", __name__, url_prefix="/klausuren")


@bp.route("/")
@login_required
def mine():
    """ Ansicht der eigenen Klausuren (Seite *Meine Klausuren*) """
    klausur_query = Klausur.query.filter(Klausur.lehrer == g.lehrer).order_by(Klausur.date.desc())

    klausuren_anstehend = klausur_query.filter(Klausur.date > datetime.now().date()).all()
    klausuren_vergangen = klausur_query.filter(Klausur.date <= datetime.now().date()).all()

    return render_template("klausuren/mine.html.j2", klausuren_anstehend=klausuren_anstehend,
                           klausuren_vergangen=klausuren_vergangen)


@bp.route("/<stufe_name>/", endpoint="stufe")
def stufe_(stufe_name):
    """ Ansicht der Klausuren einer Stufe (Seite *Klausuren [Stufe]*) """
    stufe = Stufe.query.filter_by(name=stufe_name).first()
    if stufe is None:
        abort(404)
        return

    dates_query = db.session.query(Klausur.date).filter_by(stufe=stufe).order_by(Klausur.date.desc())
    dates_anstehend = [t.date for t in dates_query.filter(Klausur.date > datetime.now().date()).distinct()]
    dates_vergangen = [t.date for t in dates_query.filter(Klausur.date <= datetime.now().date()).distinct()]

    return render_template("klausuren/stufe.html.j2", stufe=stufe, dates_anstehend=dates_anstehend,
                           dates_vergangen=dates_vergangen)


@bp.route("/<stufe_name>/add", methods=("GET", "POST"))
@beratungslehrer_required
def add(stufe_name):
    """ Klausurhinzufügung """
    reload_resp = redirect(url_for(".add", stufe_name=stufe_name), code=303)

    stufe = Stufe.query.filter_by(name=stufe_name).first()
    if stufe is None:
        abort(404)
        return

    if not g.lehrer.can_access(stufe):
        abort(403)
        return

    if request.method != "POST":
        return render_template("klausuren/add.html.j2", stufe=stufe)

    # ELSE

    kursname = request.form["kursname"]
    lehrer_id = request.form["lehrer"]
    date_str = request.form["date"]
    try:
        startperiod = int(request.form["startperiod"])
        endperiod = int(request.form["endperiod"])
    except ValueError:
        abort(400)
        return

    if startperiod < 0 or startperiod > endperiod or endperiod.bit_length() > 32:
        flash("Ungültiger Zeitraum", "error")
        return reload_resp

    if not kursname:
        flash("Bitte geben Sie einen Kursnamen an.", "error")
        return reload_resp

    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        abort(400)
        return

    lehrer = Lehrer.query.filter_by(id=lehrer_id).first()
    if lehrer is None:
        abort(400)
        return

    new_klausur = Klausur(kursname=kursname, date=date, startperiod=startperiod, endperiod=endperiod, stufe=stufe,
                          lehrer=lehrer)
    db.session.add(new_klausur)
    db.session.commit()

    flash("Die Klausur wurde erfolgreich hinzugefügt.", "success")
    current_app.logger.info(f"{g.lehrer} hat die Klausur {new_klausur} hinzugefügt.")
    return redirect(url_for(".edit", klausur_id=new_klausur.id), code=303)


@bp.route("/<int:klausur_id>", methods=("GET", "POST"))
@login_required
def edit(klausur_id):
    """ Klausurbearbeitung """
    klausur = Klausur.query.filter_by(id=klausur_id).first()
    if klausur is None:
        abort(404)
        return

    if not g.lehrer.can_access(klausur.stufe) and klausur.lehrer != g.lehrer:
        abort(403)
        return

    # ELSE
    if request.method != "POST":
        kt_list = Klausurteilnahme.query \
            .filter_by(klausur=klausur) \
            .join(Schueler) \
            .order_by(Schueler.nachname, Schueler.vorname) \
            .all()

        not_in_klausur_list = Schueler.query \
            .filter_by(stufe=klausur.stufe) \
            .filter(Schueler.id.notin_(db.session.query(Klausurteilnahme.schueler_id).filter_by(klausur=klausur))) \
            .order_by(Schueler.nachname, Schueler.vorname) \
            .all()

        return render_template("klausuren/edit.html.j2", klausur=klausur, kt_list=kt_list,
                               not_in_klausur_list=not_in_klausur_list)

    # ELSE
    reload_resp = redirect(url_for(".edit", klausur_id=klausur_id), code=303)

    exit_resp: Response
    if klausur.lehrer == g.lehrer:
        exit_resp = redirect(url_for(".mine"), code=303)
    else:
        exit_resp = redirect(url_for(".stufe", stufe_name=klausur.stufe.name), code=303)

    if klausur.edited and not g.lehrer.can_access(klausur.stufe):
        abort(400)
        return

    action = request.form["action"]

    if action == "edit":
        lehrer_can_access = g.lehrer.can_access(klausur.stufe)

        annotation = request.form["annotation"].strip()
        flag_as_edited = ("flag-as-edited" in request.form)

        klausur_laenge_str = request.form.get("laenge", None)
        print(klausur_laenge_str)
        if lehrer_can_access and not klausur_laenge_str:
            klausur_laenge = None
        else:
            try:
                klausur_laenge = int(klausur_laenge_str)
            except ValueError:
                abort(400)
                return
        print(klausur_laenge)
        klausur.laenge = klausur_laenge

        for kt in Klausurteilnahme.query.filter_by(klausur=klausur).all():
            kt.versaeumt = (f"s_{kt.schueler.id}" in request.form)

        if annotation:
            if len(annotation) > config["klausuren"]["max-annotation-length"]:
                abort(400)
                return
            klausur.annotation = annotation
        else:
            klausur.annotation = None

        if lehrer_can_access:
            klausur.edited = flag_as_edited
        else:
            klausur.edited = True

        current_app.logger.info(f"{g.lehrer} hat die Klausur {klausur} bearbeitet.")
        flash("Klausur erfolgreich bearbeitet.", "success")
        db.session.commit()

        return exit_resp

    elif action == "edit-advanced":
        if not g.lehrer.can_access(klausur.stufe):
            abort(400)
            return

        new_lehrer_id = request.form["new-lehrer"]
        new_date_str = request.form["new-date"]
        try:
            new_startperiod = int(request.form["new-startperiod"])
            new_endperiod = int(request.form["new-endperiod"])
        except ValueError:
            abort(400)
            return

        if new_startperiod < 0 or new_startperiod > new_endperiod or new_endperiod.bit_length() > 32:
            flash("Ungültiger Zeitraum", "error")
            return reload_resp

        try:
            new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
        except ValueError:
            abort(400)
            return

        new_lehrer = Lehrer.query.filter_by(id=new_lehrer_id).first()
        if new_lehrer is None:
            abort(400)
            return

        klausur.lehrer = new_lehrer
        klausur.date = new_date
        klausur.startperiod = new_startperiod
        klausur.endperiod = new_endperiod

        current_app.logger.info(f"{g.lehrer} hat die Klausur {klausur} erweitert bearbeitet.")
        flash("Klausur erfolgreich bearbeitet.", "success")
        db.session.commit()

        return reload_resp

    elif action == "delete":
        if not g.lehrer.can_access(klausur.stufe):
            abort(400)
            return

        current_app.logger.info(f"{g.lehrer} hat die Klausur {klausur} gelöscht.")
        flash("Die Klausur wurde erfolgreich gelöscht.", "success")

        db.session.delete(klausur)
        db.session.commit()
        return exit_resp

    elif action == "add-schueler":
        schueler_id = request.form.get("added-schueler", None)
        add_to = request.form["add-to"]

        if schueler_id is None:
            flash("Bitte wählen Sie einen Schüler zum Hinzufügen aus.", "error")
            return reload_resp

        is_new = False
        if schueler_id == "new-schueler":
            is_new = True
            new_schueler_nachname = request.form["new-schueler-nachname"].strip()
            new_schueler_vorname = request.form["new-schueler-vorname"].strip()
            new_schueler_stammschule_kuerzel = request.form.get("new-schueler-stammschule", None)

            stammschule = None
            if new_schueler_stammschule_kuerzel:
                stammschule = Koopschule.query.filter_by(kuerzel=new_schueler_stammschule_kuerzel).first()

                if stammschule is None:
                    abort(400)
                    return

            if not new_schueler_nachname or not new_schueler_vorname:
                flash("Bitte geben Sie einen vollständigen Namen für den neuen Schüler an.", "error")
                return reload_resp

            schueler = Schueler(id=get_next_new_schueler_id(), nachname=new_schueler_nachname,
                                vorname=new_schueler_vorname, stufe=klausur.stufe,
                                stammschule=stammschule)
            db.session.add(schueler)

        else:
            schueler = Schueler.query.filter_by(id=schueler_id).first()
            if schueler is None:
                abort(400)
                return

        if Klausurteilnahme.query.filter_by(klausur=klausur, schueler=schueler).first() is not None:
            abort(400)
            return

        if add_to == "klausur":
            klausuren = [klausur]
        elif add_to == "kurs":
            klausuren = Klausur.query.filter_by(stufe=klausur.stufe).filter_by(kursname=klausur.kursname).all()
        else:
            abort(400)
            return

        for k in klausuren:
            kt_entity = Klausurteilnahme(klausur=k, schueler=schueler)
            db.session.add(kt_entity)

        current_app.logger.info(f"{g.lehrer} hat den{' neuen' if is_new else ''} Schüler {schueler} "
                                f"zur Klausur {klausur} hinzugefügt.")

        db.session.commit()
        return reload_resp

    elif action == "remove-schueler":
        for kt in Klausurteilnahme.query.join(Klausur)\
                .filter_by(stufe=klausur.stufe)\
                .filter_by(kursname=klausur.kursname)\
                .all():
            if f"r_{kt.schueler.id}" in request.form:
                db.session.delete(kt)
                current_app.logger.info(f"{g.lehrer} hat den Schüler {kt.schueler} aus der Klausur "
                                        f"{kt.klausur} entfernt.")

        db.session.commit()
        return reload_resp

    else:
        # Bad Request, wenn ungültige action
        abort(400)
