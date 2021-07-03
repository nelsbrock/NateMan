# NateMan – Nachschreibtermin-Manager
# config_manager.py
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
Enthält Funktionen zum Laden/Erstellen der Konfigurationsdatei.
"""

import os
from shutil import copyfile

import yaml

config: dict = {}


def read_config_file(app):
    """Liest die Konfigurationsdatei."""
    with open(os.path.join(app.instance_path, "config.yml"), "r", encoding="utf-8") as yaml_file:
        yamlobj = yaml.safe_load(yaml_file)
        if not isinstance(yamlobj, dict):
            raise RuntimeError(f"Invalid config file: yaml.load returned an object "
                               f"of type {type(yamlobj).__name__} instead of a dict")

    config.clear()
    config.update(yamlobj)


def create_config_file(app) -> str:
    """Initialisiert die Konfigurationsdatei und gibt den Pfad der neuen Datei zurück."""
    new_file_path = os.path.join(app.instance_path, "config.yml")
    copyfile(
        os.path.join(app.root_path, "resources", "default-config.yml"),
        new_file_path
    )
    return new_file_path


def config_file_exists(app) -> bool:
    """Überprüft, ob die Konfigurationsdatei existiert."""
    return os.path.isfile(
        os.path.join(app.instance_path, "config.yml")
    )
