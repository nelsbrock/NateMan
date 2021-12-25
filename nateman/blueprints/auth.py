# NateMan – Nachschreibtermin-Manager
# blueprints/auth.py
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
Authentifizierungs-Blueprint
"""

import functools
import time
from datetime import datetime, timedelta
from smtplib import SMTPRecipientsRefused

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for, make_response

from .. import emails, util
from ..config_manager import config
from ..models import Lehrer, db, Session

bp = Blueprint("auth", __name__)

SESSION_COOKIE_NAME = "login_session"


@bp.before_app_request
def load_logged_in_lehrer():
    """
    Lädt den angemeldeten Lehrer vor jeder HTTP-Anfrage in die g.lehrer-Variable.
    """
    session_key = request.cookies.get(SESSION_COOKIE_NAME)
    session = Session.get(session_key)

    g.session = session

    if g.session is None:
        g.lehrer = None
    else:
        g.lehrer = g.session.lehrer


@bp.after_app_request
def clear_rotten_session_cookie(response):
    """
    Löscht veraltete Session-Cookies.
    """
    if request.cookies.get(SESSION_COOKIE_NAME) and not g.lehrer:
        response.delete_cookie(SESSION_COOKIE_NAME)

    return response


def login_required(view):
    """
    Dieser Decorator kann an Views angehängt werden, die einen angemeldeten Lehrer erfordern.
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):

        # Kein Lehrer angemeldet?
        if g.lehrer is None:
            flash("Bitte melden Sie sich an.", "error")
            return redirect(url_for("auth.login", r=request.path), code=303)

        # muss der Lehrer sein Passwort ändern?
        if g.lehrer and not g.lehrer.pwd_changed:
            return redirect(url_for("auth.password_change"), code=303)

        return view(**kwargs)

    return wrapped_view


def beratungslehrer_required(view):
    """
    Dieser Decorator kann an Views angehängt werden,
    die einen angemeldeten Beratungslehrer oder Administrator erfordern.
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):

        # Kein Lehrer angemeldet?
        if g.lehrer is None:
            flash("Bitte melden Sie sich an.", "error")
            return redirect(url_for("auth.login", r=request.path), code=303)

        # Lehrer kein Beratungslehrer oder Administrator?
        if not g.lehrer.can_access():
            abort(403)
            return

        # muss der Lehrer sein Passwort ändern?
        if g.lehrer and not g.lehrer.pwd_changed:
            return redirect(url_for("auth.password_change"), code=303)

        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    """
    Dieser Decorator kann an Views angehängt werden, die einen angemeldeten Administrator erfordern.
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):

        # Kein Lehrer angemeldet?
        if g.lehrer is None:
            flash("Bitte melden Sie sich an.", "error")
            return redirect(url_for("auth.login", r=request.path), code=303)

        # Lehrer kein Administrator?
        if not g.lehrer.is_admin:
            abort(403)
            return

        # muss der Lehrer sein Passwort ändern?
        if g.lehrer and not g.lehrer.pwd_changed:
            return redirect(url_for("auth.password_change"), code=303)

        return view(**kwargs)

    return wrapped_view


@bp.route("/login", methods=("GET", "POST"))
def login():
    """ Anmeldung (Seite *Anmelden*)"""
    if request.method != "POST":
        return render_template("auth/login.html.j2")

    # ELSE

    request_start_time = time.process_time()

    kuerzel = request.form["kuerzel"].strip()
    password = request.form["password"]
    remember_me = ("remember-me" in request.form)

    error = False

    lehrer = Lehrer.query.filter_by(kuerzel=kuerzel).first()

    # existiert Lehrer nicht?
    if lehrer is None:
        error = True
        current_app.logger.info(f"Fehlgeschlagener Anmeldeversuch von {request.remote_addr} "
                                f"(Ungültiges Kürzel '{kuerzel}')")

    # ist das Passwort falsch?
    elif not lehrer.check_password(password):
        error = True
        current_app.logger.info(f"Fehlgeschlagener Anmeldeversuch von {request.remote_addr} "
                                f"(Falsches Passwort für {lehrer.kuerzel})")

    if error:
        # Bei fehlgeschlagenem Anmeldeversuch 2 Sekunden vor Antwort warten
        time.sleep(request_start_time - time.process_time() + 2)
        flash("Ungültige Anmeldedaten.", "error")
        return redirect(url_for(".login", r=request.args.get("r", None)), code=303)

    # Kein Fehler -> Lehrer anmelden

    current_app.logger.info(f"{lehrer} hat sich angemeldet.")

    session_expiry_delta = timedelta(
        minutes=(config["auth"]["session-remember-me-duration"] if remember_me else config["auth"]["session-duration"])
    )
    session = Session.create(lehrer, session_expiry_delta)

    if not lehrer.pwd_changed:
        red = redirect(url_for(".password_change"), code=303)

    else:
        redirect_path = request.args.get("r", None)
        # Wenn ein Weiterleitungspfad als GET-Parameter übergeben wurde
        # (wie es z.B. der login_required-Wrapper macht, wenn kein Benutzer
        # angemeldet ist), auf diesen Pfad weiterleiten, falls er mit einem
        # Schrägstrich beginnt (also kein externer Link ist).
        if redirect_path and len(redirect_path) > 0 and redirect_path[0] == "/":
            red = redirect(redirect_path, code=303)
        else:
            red = redirect(url_for("klausuren.mine"), code=303)

    db.session.commit()

    resp = make_response(red)
    resp.set_cookie(SESSION_COOKIE_NAME, session.key,
                    max_age=session_expiry_delta.total_seconds() if remember_me else None,
                    expires=session.expiry if remember_me else None, secure=config["uses-ssl"], httponly=True,
                    samesite="Strict")
    return resp


@bp.route("/logout")
def logout():
    """ Abmeldung (Seite *Abmelden*)"""
    resp = make_response(redirect(url_for("auth.login"), code=303))
    if g.lehrer:
        current_app.logger.info(f"{g.lehrer} hat sich abgemeldet.")
        resp.delete_cookie("login_session")
        db.session.delete(g.session)
        db.session.commit()

    return resp


@bp.route("/confirm-email")
def confirm_email():
    """ Emailbestätigung """
    red = redirect(url_for(".login" if g.lehrer is None else "klausuren.mine"), code=303)

    token = request.args.get("token", None)

    if token is None:
        flash("Ungültiger/veralteter Bestätigungslink.", "alert")
        return red

    lehrer = Lehrer.query.filter_by(confirmation_token=token).first()

    if lehrer is None:
        flash("Ungültiger/veralteter Bestätigungslink.", "alert")
        return red

    # ELSE

    lehrer.confirmation_token = None
    lehrer.is_confirmed = True
    db.session.commit()

    current_app.logger.info(f"{lehrer} hat die eigene E-Mail-Adresse ({lehrer.email}) bestätigt.")
    flash("Die E-Mail-Adresse wurde erfolgreich bestätigt.", "success")

    return red


@bp.route("/password-change", methods=("GET", "POST"))
def password_change():
    """ Passwortänderung nach erstem Login """
    # login_required kann hier nicht verwendet werden,
    # da es ein verändertes Passwort erfordert
    if not g.lehrer:
        return redirect(url_for("auth.login"), code=303)

    if g.lehrer.pwd_changed:
        return redirect(url_for(".account"), code=303)

    if request.method != "POST":
        return render_template("auth/password-change.html.j2")

    # ELSE

    new_pass = request.form["new-password"]
    new_pass_confirm = request.form["new-password-confirm"]

    error_msg = None

    if not new_pass or not new_pass_confirm:
        error_msg = "Bitte geben Sie ein neues Passwort ein."

    # ist das neue Passwort kürzer als 6 Zeichen?
    if len(new_pass) < 6:
        error_msg = "Das neue Passwort muss mindestens 6 Zeichen lang sein."
    # ist das neue Passwort zu groß?
    elif not util.validate_bcrypt_password(new_pass):
        error_msg = "Das neue Passwort darf höchstens 72 Zeichen lang sein."
    # stimmen die neuen Passwörter nicht überein?
    elif new_pass != new_pass_confirm:
        error_msg = "Die neuen Passwörter stimmen nicht überein."

    # Änderungen vornehmen, falls kein Fehler aufgetreten ist
    if error_msg:
        # Es ist ein Fehler aufgetreten
        flash(error_msg, "error")
        return redirect(url_for(".account"), code=303)

    g.lehrer.set_password(new_pass)
    db.session.commit()

    current_app.logger.info(f"{g.lehrer} hat das eigene Passwort geändert.")

    return redirect(url_for("klausuren.mine"), code=303)


@bp.route("/password-reset", methods=("GET", "POST"))
def password_reset():
    """ Passwortzurücksetzung (Seite *Passwort vergessen*)"""
    red = redirect(url_for(".login" if g.lehrer is None else "klausuren.mine"), code=303)

    token = request.args.get("token", None)

    t_lehrer = None
    if token is not None:
        t_lehrer = Lehrer.query.filter_by(password_reset_token=token).first()

        expired = False
        if t_lehrer is not None:
            expired = t_lehrer.password_reset_expiry < datetime.utcnow()
            if expired:
                t_lehrer.password_reset_token = None
                t_lehrer.password_reset_expiry = None
                db.session.commit()

        if t_lehrer is None or expired:
            flash("Ungültiger/veralteter Zurücksetzungslink.", "alert")
            return red

    if request.method == "POST":
        if token is None:
            # --- Antragstellung ---
            lehrer_kuerzel = request.form["lehrer-kuerzel"]
            email_address = request.form["email-address"]

            lehrer = Lehrer.query.filter_by(kuerzel=lehrer_kuerzel, email=email_address).first()

            if lehrer is None:
                flash("Es gibt keine Lehrkraft mit den angegebenen Kriterien.", "error")
                return redirect(url_for(".password_reset"), code=303)

            if not lehrer.is_confirmed:
                flash("Es gibt eine Lehrkraft mit den angegebenen Kriterien, allerdings ist deren "
                      "E-Mail-Adresse nicht bestätigt.\nWenden Sie sich an einen Administrator.", "error")
                return redirect(url_for(".password_reset"), code=303)

            new_token = util.random_uri_safe_string(64)
            lehrer.password_reset_token = new_token
            lehrer.password_reset_expiry = datetime.utcnow() + timedelta(hours=1)

            # Zurücksetzungsemail senden
            try:
                emails.send_password_reset_mail(lehrer.kuerzel, lehrer.email, new_token)
            except SMTPRecipientsRefused:
                flash(f"Es konnte keine E-Mail an {lehrer.email} gesendet werden.\n"
                      f"Wahrscheinlich existiert diese Adresse nicht mehr.\n"
                      f"Wenden Sie sich an einen Administrator.", "error")
                return redirect(url_for(".password_reset"), code=303)

            db.session.commit()

            flash("Sie müssten nun eine E-Mail bekommen mit einem Link, über den Sie Ihr Passwort ändern können.\n"
                  "Der Link ist eine Stunde lang gültig.", "success")
            current_app.logger.info(f"Für {lehrer} wurde eine Passwortzurücksetzung beantragt.")

        else:
            # --- Passwortänderung ---
            new_pass = request.form["new-password"]
            new_pass_confirm = request.form["new-password-confirm"]
            error_msg = None
            # ist das neue Passwort kürzer als 6 Zeichen?
            if len(new_pass) < 6:
                error_msg = "Das neue Passwort muss mindestens 6 Zeichen lang sein."
            # ist das neue Passwort zu groß?
            elif not util.validate_bcrypt_password(new_pass):
                error_msg = "Das neue Passwort darf höchstens 72 Zeichen lang sein."
            # stimmen die neuen Passwörter nicht überein?
            elif new_pass != new_pass_confirm:
                error_msg = "Die neuen Passwörter stimmen nicht überein."

            if error_msg:
                flash(error_msg, "error")
                return redirect(url_for(".password_reset", token=token), code=303)

            # ELSE

            t_lehrer.password_reset_token = None
            t_lehrer.set_password(new_pass)
            db.session.commit()

            current_app.logger.info(f"{t_lehrer} hat das eigene Passwort zurückgesetzt.")
            flash("Das Passwort wurde erfolgreich zurückgesetzt.", "success")

        return red

    else:
        if token is None:
            # --- Formular zur Antragstellung ---
            return render_template("auth/password-reset-send.html.j2")
        else:
            # --- Formular zur Passwortänderung ---
            return render_template("auth/password-reset-do.html.j2")


@bp.route("/account", methods=("GET", "POST"))
@login_required
def account():
    """ Kontoeinstellungen (Seite *Mein Konto*) """
    if request.method != "POST":
        return render_template("auth/account.html.j2")

    # ELSE

    current_password = request.form["current-password"]
    new_email = request.form["new-email"].strip() or None
    new_pass = request.form["new-password"]
    new_pass_confirm = request.form["new-password-confirm"]

    error_msg = None

    change_kuerzel = False
    change_email = False
    change_password = False

    # ist das aktuelle Passwort falsch?
    if not g.lehrer.check_password(current_password):
        error_msg = "Falsches aktuelles Passwort."
    else:
        # Neue E-Mail-Adresse, falls angegeben und nicht die aktuelle Adresse
        if new_email != g.lehrer.email:
            change_email = True
            # ist die neue E-Mail-Adresse syntaktisch ungültig?
            if new_email is not None and not util.EMAIL_ADDRESS_REGEX.match(new_email):
                error_msg = "Bitte geben Sie eine gültige E-Mail-Adresse ein."

        # Neues Passwort, falls angegeben
        if new_pass:
            change_password = True
            # ist das neue Passwort kürzer als 6 Zeichen?
            if len(new_pass) < 6:
                error_msg = "Das neue Passwort muss mindestens 6 Zeichen lang sein."
            # ist das neue Passwort zu groß?
            elif not util.validate_bcrypt_password(new_pass):
                error_msg = "Das neue Passwort darf höchstens 72 Zeichen lang sein."
            # stimmen die neuen Passwörter nicht überein?
            elif new_pass != new_pass_confirm:
                error_msg = "Die neuen Passwörter stimmen nicht überein."

    # Änderungen vornehmen, falls kein Fehler aufgetreten ist
    if error_msg:
        # Es ist ein Fehler aufgetreten
        flash(error_msg, "error")
        return redirect(url_for(".account"), code=303)

    # ELSE
    if not change_kuerzel and not change_email and not change_password:
        return redirect(url_for(".account"), code=303)

    if change_email:
        if new_email is not None:
            token = util.random_uri_safe_string(32)
            # Bestätigungsemail senden
            try:
                emails.send_confirmation_link_mail(g.lehrer.kuerzel, new_email, token)
            except SMTPRecipientsRefused:
                flash(f"Wir konnten keine Bestätigungsemail an {new_email} senden. "
                      f"Wahrscheinlich existiert diese Adresse nicht.", "error")
                return redirect(url_for(".account"), code=303)

            g.lehrer.confirmation_token = token

        old_email = g.lehrer.email
        g.lehrer.email = new_email
        g.lehrer.is_confirmed = new_email is None

        current_app.logger.info(f"{g.lehrer} hat die eigene E-Mail-Adresse von {old_email} "
                                f"auf {g.lehrer.email} geändert.")

    if change_password:
        g.lehrer.set_password(new_pass)
        current_app.logger.info(f"{g.lehrer} hat das eigene Passwort geändert.")

    db.session.commit()
    flash("Benutzerdaten erfolgreich geändert.", "success")
    return redirect(url_for(".account"), code=303)
