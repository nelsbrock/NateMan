# NateMan – Nachschreibtermin-Manager
# blueprints/admin/__init__.py
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
Administrations-Blueprint
"""

from flask import Blueprint, flash, g, redirect, render_template, request, url_for, current_app
from sqlalchemy.exc import StatementError

from ..auth import admin_required
from ...models import db

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def index():
    """ enthält Links zur Administration (Seite *Administration*)"""
    return render_template("admin/index.html.j2")


@bp.route("/sql-access", methods=("GET", "POST"))
@admin_required
def sql_access():
    """ SQL-Zugriffsseite """
    reload_response = redirect(url_for(".sql_access"), code=303)

    if request.method != "POST":
        return render_template("admin/sql_access.html.j2", query="", result=None)

    # ELSE

    query = request.form["query"].strip()

    if not query:
        flash("Bitte geben Sie eine SQL-Abfrage ein.", "error")
        return reload_response

    # Query ausführen
    try:
        result = db.session.execute(query)
    except StatementError as exc:
        flash(f"Die SQL-Abfrage konnte nicht ausgeführt werden.\n\nFehlerbeschreibung:\n{exc.orig}", "error")
        return render_template("admin/sql_access.html.j2", query=query, result=None)

    if not result.returns_rows:
        db.session.commit()

    logged_query = query.replace('\r\n', ' ').replace('\n', ' ')
    current_app.logger.info(f"{g.lehrer} hat eine SQL-Abfrage ausgeführt: {logged_query}")
    flash("Die SQL-Abfrage wurde erfolgreich ausgeführt.", "success")

    return render_template("admin/sql_access.html.j2", query=query, result=result)
