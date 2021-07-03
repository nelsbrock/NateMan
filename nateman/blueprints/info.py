# NateMan – Nachschreibtermin-Manager
# blueprints/info.py
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
Informations-Blueprint
"""

from flask import Blueprint, render_template

bp = Blueprint("info", __name__, url_prefix="/info")


@bp.route("/licenses")
def licenses():
    """ Lizenzen """
    return render_template("info/licenses.html.j2")
