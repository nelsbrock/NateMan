# NateMan – Nachschreibtermin-Manager
# util.py
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
Enthält nützliche, von NateMan unabhängige Funktionen.
"""

import random
import re

from datetime import date

EMAIL_ADDRESS_REGEX = re.compile(r"^[a-zA-Z0-9!#$%&‘*+–/=?^_`{|}~](\.?[a-zA-Z0-9!#$%&‘*+–/=?^_`{|}~])*"
                                 r"@[a-zA-Z0-9-](\.?[a-zA-Z0-9-])*$")

_RUASS_TRANSLATION = {ord("ä"): "ae", ord("Ä"): "Ae",
                      ord("ö"): "oe", ord("Ö"): "Oe",
                      ord("ü"): "ue", ord("Ü"): "Ue",
                      ord("ß"): "ss", ord("ẞ"): "Ss"}
""" Übersetzungstabelle für replace_umlauts_and_sharp_s """


def email_address_safe(s: str) -> str:
    """
    Ersetzt die Buchstaben ä, ö, ü und ß (als Klein- oder Großbuchstabe) im String s durch die entsprechende
    Zeichenfolge ohne Umlaute bzw. Eszett und wandelt alle Buchstaben in Kleinbuchstaben um.
    von Niklas Elsbrock.
    """
    return s.translate({
        ord("ä"): "ae", ord("Ä"): "Ae",
        ord("ö"): "oe", ord("Ö"): "Oe",
        ord("ü"): "ue", ord("Ü"): "Ue",
        ord("ß"): "ss", ord("ẞ"): "Ss"
    }).lower()


_URI_SAFE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
""" Zeichensatz für :func:`random_uri_safe_string` """

_SYSTEM_RANDOM = random.SystemRandom()


def random_uri_safe_string(length: int) -> str:
    """
    Generiert einen zufälligen String der Länge ``length`` aus URI-freundlichen Zeichen
    (Buchstaben, Bindestrich, Unterstrich).
    von Niklas Elsbrock.

    :param length: Länge des zu generierenden Strings
    :return: generierter String
    """
    return "".join(_SYSTEM_RANDOM.choice(_URI_SAFE_CHARS) for _ in range(length))


def validate_bcrypt_password(password: str) -> bool:
    """
    Überprüft, ob der übergebene String ``password`` als Passwort verwendet werden kann
    (d.h. ob das Passwort höchstens 72 Bytes groß ist).
    von Niklas Elsbrock.

    :param password: zu validierender String
    :return: ``True`` falls ja, ``False`` falls nein
    """
    return len(password.encode("utf-8")) <= 72


def format_date(date_: date) -> str:
    """
    Formatiert ein Datumsobjekt nach dem deutschen Datumsformat, inklusive Wochentagkürzel (WW, DD.MM.YYYY).
    von Niklas Elsbrock.

    :param date_: zu formatierendes Datum
    :return: formatiertes Datum als String
    """
    return date_.strftime("%a, %d.%m.%Y")


def is_integer_string(s: str) -> bool:
    """
    Überprüft, ob der String ``s`` in einen Integer umgewandelt werden kann

    :param s: zu überprüfender String
    :return: ``True`` falls ja, ``False`` falls nein
    """
    try:
        int(s)
    except ValueError:
        return False
    else:
        return True
