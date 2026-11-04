import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_wtf.csrf import CSRFError

from .extensions import db, login_manager, csrf
from sqlalchemy import text



def create_app(test_config=None):
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            "mysql+mysqlconnector://root:password@127.0.0.1/RampCoreOs",
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,

        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=False, #This is for development only!! Set to True when using in production
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return jsonify({
            "error": "CSRF validation failed",
            "message": error.description
        }), 400

    
    CORS(
        app,
        origins=["http://localhost:5173"], # For development only, need to change to actual URL once in production
        supports_credentials=True,
    )

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from src.api import models
    from src.api.routes.auth import auth_bp
    from src.api.routes.main import main_bp
    from src.api.routes.admin import admin_bp
    from src.api.routes.account import account_bp
    from src.api.routes.projects import projects_bp
    from src.api.routes.project_detail import project_detail_bp

    app.config.setdefault("UPLOAD_FOLDER", "uploads")

    app.register_blueprint(main_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(account_bp, url_prefix="/api")
    app.register_blueprint(projects_bp, url_prefix="/api")
    app.register_blueprint(project_detail_bp, url_prefix="/api")

    
    return app

