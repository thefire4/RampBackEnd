from flask_login import UserMixin
from .extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(
        db.String(80), unique = True, nullable= False
    )
    password_hash = db.Column(
        db.String(255), nullable = False
    )

from .extensions import login_manager

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))