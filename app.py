import os
import logging
from flask import Flask, render_template
from extensions import db, bcrypt, login_manager, csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger


def create_app():
    app = Flask(__name__)

    instance_path = os.path.join(os.getcwd(), "instance")
    os.makedirs(instance_path, exist_ok=True)
    db_url = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(instance_path, 'database.db')}"
    )

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "stegano-secret-dev-key-2024"),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=500 * 1024 * 1024,
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=None,
    )

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )

    Swagger(
        app,
        config={
            "headers": [],
            "specs": [
                {
                    "endpoint": "apispec_1",
                    "route": "/apispec_1.json",
                    "rule_filter": lambda r: True,
                    "model_filter": lambda t: True,
                }
            ],
            "static_url_path": "/flasgger_static",
            "swagger_ui": True,
            "specs_route": "/apidocs/",
        },
        template={
            "info": {
                "title": "Deep Steganography API",
                "description": "API endpoints for the AI Steganography Project",
                "version": "1.0.0",
            }
        },
    )

    @login_manager.user_loader
    def load_user(user_id):
        from models.db_models import User

        return User.query.get(int(user_id))

    # Register blueprints
    from routes.auth.routes import auth_bp
    from routes.hide.routes import hide_bp
    from routes.extract.routes import extract_bp
    from routes.history.routes import history_bp
    from routes.api.routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(hide_bp)
    app.register_blueprint(extract_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(api_bp)

    csrf.exempt(hide_bp)
    csrf.exempt(extract_bp)
    csrf.exempt(api_bp)

    def get_dashboard_metrics(user_id):
        from models.db_models import History

        try:
            user_history = History.query.filter_by(user_id=user_id).all()
            secrets_hidden = sum(1 for r in user_history if r.operation == "hide")
            secrets_extracted = sum(1 for r in user_history if r.operation == "extract")
            psnr_vals = [
                r.psnr_value
                for r in user_history
                if r.operation == "hide" and r.psnr_value is not None
            ]
            robustness_vals = [
                r.robustness_score
                for r in user_history
                if r.operation == "hide" and r.robustness_score is not None
            ]
            avg_psnr = round(sum(psnr_vals) / len(psnr_vals), 2) if psnr_vals else None
            avg_robustness = (
                round(sum(robustness_vals) / len(robustness_vals), 1)
                if robustness_vals
                else None
            )
        except Exception:
            secrets_hidden = 0
            secrets_extracted = 0
            avg_psnr = None
            avg_robustness = None
        return {
            "secrets_hidden": secrets_hidden,
            "secrets_extracted": secrets_extracted,
            "avg_psnr": avg_psnr,
            "avg_robustness": avg_robustness,
        }

    @app.route("/")
    def index():
        from flask_login import current_user

        if current_user.is_authenticated:
            metrics = get_dashboard_metrics(current_user.id)
            return render_template("dashboard.html", **metrics)
        return render_template("index.html")

    @app.route("/dashboard")
    def dashboard():
        from flask_login import current_user
        from flask import redirect, url_for

        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        metrics = get_dashboard_metrics(current_user.id)
        return render_template("dashboard.html", **metrics)

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/contact")
    def contact():
        return render_template("contact.html")

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("413.html"), 413

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    # Create database tables
    with app.app_context():
        try:
            os.makedirs(app.instance_path, exist_ok=True)
            db.create_all()
        except Exception as e:
            logging.warning(f"DB init warning: {e}")

    logging.basicConfig(level=logging.INFO)

    return app


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(debug=True, host="0.0.0.0", port=5000)
