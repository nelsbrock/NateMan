# NateMan – Nachschreibtermin-Manager
# blueprints/schueler.py
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
Schüler-Blueprint
"""
from typing import Dict, List, Tuple

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for

from .auth import beratungslehrer_required
from ..models import Klausurteilnahme, db, Schueler, Klausur, Stufe

bp = Blueprint("schueler", __name__, url_prefix="/schueler")


@bp.route("/versaeumnisse/", methods=("GET", "POST"))
@beratungslehrer_required
def versaeumnisse():
    """ Versäumnisliste (Seite *Versäumnisse*) """
    if request.method != "POST":
        versaeumt_dict: Dict[Stufe, Tuple[List[Klausurteilnahme], List[Klausurteilnahme]]] = {}
        for stufe in g.lehrer.accessible_stufen():
            base_query = Klausurteilnahme.query.join(Schueler).join(Klausur) \
                .filter(Klausurteilnahme.versaeumt) \
                .filter(Klausur.stufe == stufe) \
                .order_by(Schueler.nachname, Schueler.vorname)

            versaeumt_dict[stufe] = (
                base_query.filter(~Klausurteilnahme.nachgeschrieben).all(),
                base_query.filter(Klausurteilnahme.nachgeschrieben).all(),
            )

        return render_template("schueler/versaeumnisse.html.j2", versaeumt_dict=versaeumt_dict)

    # ELSE

    for kt in Klausurteilnahme.query.filter_by(versaeumt=True).all():
        if g.lehrer.can_access(kt.klausur.stufe):
            kt.attestiert = (f"a_{kt.klausur.id}:{kt.schueler.id}" in request.form)
            kt.nachgeschrieben = (f"n_{kt.klausur.id}:{kt.schueler.id}" in request.form)

    current_app.logger.info(f"{g.lehrer} hat die Versäumnisliste bearbeitet.")
    flash("Versäumnisliste erfolgreich bearbeitet.", "success")
    db.session.commit()

    return redirect(url_for(".versaeumnisse"), code=303)
