from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import Index

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

F = TypeVar("F", bound=Callable)

DEMO_USERS = (
    ("alex", "Alex Rivera", "alex@example.test", False),
    ("jordan", "Jordan Lee", "jordan@example.test", False),
    ("casey", "Casey Morgan", "casey@example.test", False),
    ("admin", "Demo Administrator", "admin@example.test", True),
)

MESSAGE_MAX_LENGTH = 500
FEED_PAGE_SIZE = 20


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    is_admin = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())


class Kudos(db.Model):
    __table_args__ = (Index("ix_kudos_feed_order", "created_at", "id"),)

    id = db.Column(db.Integer, primary_key=True)
    sender_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.String(MESSAGE_MAX_LENGTH), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    is_visible = db.Column(
        db.Boolean, nullable=False, default=True, server_default=db.true()
    )

    sender = db.relationship("User", foreign_keys=[sender_user_id])
    recipient = db.relationship("User", foreign_keys=[recipient_user_id])


def seed_demo_users() -> None:
    for username, display_name, email, is_admin in DEMO_USERS:
        user = db.session.execute(
            db.select(User).where(User.username == username)
        ).scalar_one_or_none()
        if user is None:
            user = User(
                username=username,
                display_name=display_name,
                email=email,
                is_active=True,
                is_admin=is_admin,
            )
            db.session.add(user)
        else:
            user.display_name = display_name
            user.email = email
            user.is_active = True
            user.is_admin = is_admin
    db.session.commit()


def login_required(view: F) -> F:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.current_user is None:
            return redirect(url_for("demo_login"))
        return view(*args, **kwargs)

    return wrapped  # type: ignore[return-value]


def admin_required(view: F) -> F:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.current_user is None:
            return redirect(url_for("demo_login"))
        if not g.current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped  # type: ignore[return-value]


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    instance_dir = Path(app.instance_path)
    instance_dir.mkdir(parents=True, exist_ok=True)
    default_database = f"sqlite:///{(instance_dir / 'kudos.sqlite3').as_posix()}"

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("KUDOS_SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=os.environ.get("KUDOS_DATABASE_URL")
        or default_database,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        KUDOS_ENV=os.environ.get("KUDOS_ENV", "local"),
        DEMO_AUTH_ENABLED=True,
    )
    if test_config:
        app.config.update(test_config)

    if app.config["KUDOS_ENV"] != "local" or not app.config["DEMO_AUTH_ENABLED"]:
        raise RuntimeError(
            "This standalone app only supports local demo authentication. "
            "Do not run it as a shared or production deployment."
        )

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    @app.before_request
    def load_current_user() -> None:
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id is not None else None
        if user is not None and not user.is_active:
            session.clear()
            user = None
        g.current_user = user

    @app.cli.command("seed-demo-users")
    def seed_demo_users_command() -> None:
        """Create or refresh the local demo accounts."""
        seed_demo_users()
        print(f"Seeded {len(DEMO_USERS)} demo users.")

    @app.get("/demo/login")
    def demo_login():
        if g.current_user is not None:
            return redirect(url_for("dashboard"))
        users = db.session.execute(
            db.select(User)
            .where(User.is_active.is_(True))
            .order_by(User.display_name)
        ).scalars()
        return render_template("login.html", users=users)

    @app.post("/demo/login")
    def demo_login_submit():
        user_id = request.form.get("user_id", type=int)
        user = db.session.get(User, user_id) if user_id is not None else None
        if user is None or not user.is_active:
            flash("Choose an active demo account.", "error")
            return redirect(url_for("demo_login"))

        session.clear()
        session["user_id"] = user.id
        flash(f"Signed in as {user.display_name}.", "success")
        return redirect(url_for("dashboard"))

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        flash("You have signed out.", "success")
        return redirect(url_for("demo_login"))

    @app.get("/")
    @login_required
    def dashboard():
        page = request.args.get("page", default=1, type=int)
        if page is None or page < 1:
            abort(404)
        pagination = db.paginate(
            db.select(Kudos)
            .where(Kudos.is_visible.is_(True))
            .order_by(Kudos.created_at.desc(), Kudos.id.desc()),
            page=page,
            per_page=FEED_PAGE_SIZE,
            error_out=False,
        )
        return render_template("dashboard.html", pagination=pagination)

    @app.route("/kudos/new", methods=["GET", "POST"])
    @login_required
    def new_kudos():
        recipients = db.session.execute(
            db.select(User)
            .where(
                User.is_active.is_(True),
                User.id != g.current_user.id,
            )
            .order_by(User.display_name)
        ).scalars().all()

        if request.method == "GET":
            return render_template(
                "kudos_form.html",
                recipients=recipients,
                selected_recipient_id="",
                message="",
            )

        message = request.form.get("message", "").strip()
        recipient_id = request.form.get("recipient_id", type=int)
        recipient = (
            db.session.get(User, recipient_id) if recipient_id is not None else None
        )
        errors = []

        if not message:
            errors.append("Enter an appreciation message.")
        elif len(message) > MESSAGE_MAX_LENGTH:
            errors.append(
                f"Messages must be {MESSAGE_MAX_LENGTH} characters or fewer."
            )
        if recipient is None or not recipient.is_active:
            errors.append("Choose an active colleague.")
        elif recipient.id == g.current_user.id:
            errors.append("You cannot give kudos to yourself.")

        if errors:
            for error in errors:
                flash(error, "error")
            return (
                render_template(
                    "kudos_form.html",
                    recipients=recipients,
                    selected_recipient_id=request.form.get("recipient_id", ""),
                    message=request.form.get("message", ""),
                ),
                400,
            )

        kudos = Kudos(
            sender_user_id=g.current_user.id,
            recipient_user_id=recipient.id,
            message=message,
        )
        db.session.add(kudos)
        db.session.commit()
        flash(f"Kudos sent to {recipient.display_name}.", "success")
        return redirect(url_for("dashboard"))

    @app.get("/admin/kudos")
    @admin_required
    def admin_kudos():
        page = request.args.get("page", default=1, type=int)
        if page is None or page < 1:
            abort(404)
        pagination = db.paginate(
            db.select(Kudos).order_by(Kudos.created_at.desc(), Kudos.id.desc()),
            page=page,
            per_page=FEED_PAGE_SIZE,
            error_out=False,
        )
        return render_template("admin_kudos.html", pagination=pagination)

    @app.post("/admin/kudos/<int:kudos_id>/hide")
    @admin_required
    def hide_kudos(kudos_id: int):
        kudos = db.session.get(Kudos, kudos_id)
        if kudos is None:
            abort(404)
        kudos.is_visible = False
        db.session.commit()
        flash("Kudos hidden from the employee feed.", "success")
        return redirect(url_for("admin_kudos"))

    @app.post("/admin/kudos/<int:kudos_id>/delete")
    @admin_required
    def delete_kudos(kudos_id: int):
        kudos = db.session.get(Kudos, kudos_id)
        if kudos is None:
            abort(404)
        db.session.delete(kudos)
        db.session.commit()
        flash("Kudos permanently deleted.", "success")
        return redirect(url_for("admin_kudos"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
