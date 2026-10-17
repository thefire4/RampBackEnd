import os

from flask import Flask, jsonify
from flask_cors import CORS

from .extensions import db, login_manager
from sqlalchemy import text




def create_app(test_config=None):
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY = os.environ["SECRET_KEY"],
        SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"],
        SQLALCHEMY_TRACK_MODIFICATIONS = False,

        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=False, #This is for development only!! Set to True when using in production
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)


    CORS(
        app,
        origins=["http://localhost:5173"], # For development only, need to change to actual URL once in production
        supports_credentials=True,
    )

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from src.api import models
    from src.api.routes.auth import auth_bp
    from src.api.routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    
    return app

