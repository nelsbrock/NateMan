# NateMan – Nachschreibtermin-Manager
# emails.py
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
Enthält Funktionen für den E-Mail-Versand.
"""

import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional, Union

from flask import current_app, render_template
from sqlalchemy.sql.elements import and_

from .config_manager import config
from .models import Klausur, Lehrer


def _smtp_create() -> Union[smtplib.SMTP, smtplib.SMTP_SSL]:
    """Erstellt die der Konfiguration entsprechende SMTP-Instanz und verbindet zum SMTP-Server."""
    logger = current_app.logger
    logger.debug("Stellt Verbindung zum SMTP-Server her...")

    smtp_constr = smtplib.SMTP_SSL if config["mail"]["use-ssl"] else smtplib.SMTP
    smtp = smtp_constr(config["mail"]["smtp"]["hostname"], config["mail"]["smtp"]["hostport"])

    smtp.login(config["mail"]["smtp"]["user"], config["mail"]["smtp"]["password"])

    logger.debug("Erfolgreich mit SMTP-Server verbunden.")

    return smtp


def _send_mail(address: str, subject: str, content: str, content_type="html", content_charset="utf-8",
               smtp: Optional[smtplib.SMTP] = None) -> None:
    """
    Sendet eine E-Mail mit den in der NateMan-Konfiguration angegebenen SMTP-Daten.

    :param address: Adresse, zu der die E-Mail gesendet werden soll
    :param subject: Betreff der E-Mail
    :param content: Inhalt der E-Mail
    :param content_type: Inhaltstyp der E-Mail
    :param content_charset: Zeichensatz des E-Mail-Inhalts
    :param smtp: SMTP-Verbindung. Falls keine Verbindung angegeben wird, wird eine erstellt
    (und nach dem E-Mail-Versand geschlossen).
    """
    logger = current_app.logger
    sender_address = config["mail"]["sender-address"]

    msg = MIMEText(content, content_type, content_charset)
    msg["From"] = f"NateMan <{sender_address}>"
    msg["Subject"] = subject

    smtp_param = smtp is not None
    if not smtp_param:
        smtp = _smtp_create()

    logger.debug(f"E-Mail wird an {address} versandt...")
    try:
        smtp.sendmail(sender_address, address, msg.as_string())
    except smtplib.SMTPRecipientsRefused as exc:
        if not smtp_param:
            smtp.close()
        logger.debug(f"E-Mail an {address} konnte nicht versandt werden "
                     f"(wahrscheinlich ungültige Adresse).", exc_info=exc)
        raise
    else:
        logger.debug(f"E-Mail an {address} erfolgreich versandt.")

    if not smtp_param:
        smtp.close()


def send_confirmation_link_mail(address: str, token: str) -> None:
    """Sendet die Bestätigungsemail nach dem Festlegen der E-Mail-Adresse."""
    content = render_template("email/confirmation.html.j2", token=token)
    _send_mail(address, "NateMan: Bestätigung der E-Mail-Adresse", content)


def send_password_reset_mail(address: str, token: str) -> None:
    """Sendet die Passwortzurücksetzungsemail."""
    content = render_template("email/password-reset.html.j2", token=token)
    _send_mail(address, "NateMan: Passwortzurücksetzung", content)


def send_reminder_mails() -> int:
    """
    Sendet Erinnerungsemails an alle Lehrer, die unbearbeitete vergangene Klausuren haben.

    :return: Anzahl der E-Mails, die nicht versandt werden konnten
    """
    logger = current_app.logger
    logger.info("Startet den Versand von Erinnerungsemails...")

    # SMTP-Connect
    smtp = _smtp_create()

    fail_count = 0
    for lehrer in Lehrer.query.all():
        not_edited_list = Klausur.query \
            .filter(and_(Klausur.date <= datetime.now().date(), Klausur.lehrer == lehrer, ~Klausur.edited)) \
            .order_by(Klausur.date.desc()).all()

        if len(not_edited_list) == 0:
            fail_count += 1
            continue

        if lehrer.email is None:
            fail_count += 1
            logger.info(f"Erinnerungsemail an {lehrer} konnte nicht versandt werden, da für diesen Lehrer keine "
                        f"E-Mail-Adresse eingetragen ist.")
            continue

        if not lehrer.is_confirmed:
            fail_count += 1
            logger.info(f"Erinnerungsemail an {lehrer} konnte nicht versandt werden, da die E-Mail-Adresse dieses "
                        f"Lehrers ({lehrer.email}) nicht bestätigt ist.")
            continue

        content = render_template("email/reminder.html.j2", not_edited_list=not_edited_list)
        try:
            _send_mail(lehrer.email, "NateMan: zur Erinnerung", content, smtp=smtp)
        except smtplib.SMTPRecipientsRefused as exc:
            logger.info(f"Erinnerungsemail an {lehrer} mit der Adresse {lehrer.email} konnte nicht versandt werden "
                        f"(wahrscheinlich ungültige Adresse).", exc_info=exc)
        else:
            logger.info(f"Erinnerungsemail an {lehrer} erfolgreich versandt.")

    smtp.close()

    if fail_count == 0:
        logger.info("Versand von Erinnerungsemails abgeschlossen.")
    else:
        logger.info(f"Versand von Erinnerungsemails abgeschlossen. "
                    f"{fail_count} E-Mail(s) konnten nicht versandt werden.")

    return fail_count
