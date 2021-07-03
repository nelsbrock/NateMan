# NateMan – Nachschreibtermin-Manager
# blueprints/error.py
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
Enthält ausschließlich Errorhandler.
"""

from flask import Blueprint, render_template

bp = Blueprint("error", __name__)


@bp.app_errorhandler(400)
def error_400(error):
    """400 - Ungültige Anfrage"""
    return render_template("error/400.html.j2"), 400


@bp.app_errorhandler(403)
def error_403(error):
    """403 - Verboten"""
    return render_template("error/403.html.j2"), 403


@bp.app_errorhandler(404)
def error_404(error):
    """404 - Seite nicht gefunden"""
    return render_template("error/404.html.j2"), 404


@bp.app_errorhandler(500)
def error_500(error):
    """500 - serverseitiger Fehler"""
    return render_template("error/500.html.j2"), 500
