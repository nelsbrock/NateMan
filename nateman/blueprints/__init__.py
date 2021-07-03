# NateMan – Nachschreibtermin-Manager
# blueprints/__init__.py
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
Index-Blueprint
"""

from flask import Blueprint, g, redirect, url_for, render_template

bp = Blueprint("index", __name__)


@bp.route("/")
def index():
    """ Startseite (Pfad ``/``, leitet bei angemeldetem Lehrer auf Klausurseite um) """
    if g.lehrer is not None:
        return redirect(url_for("klausuren.mine"), code=303)
    else:
        return render_template("index/index.html.j2")
