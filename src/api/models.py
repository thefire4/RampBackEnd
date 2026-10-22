from flask_login import UserMixin
from .extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(
        db.String(80),
        unique = True,
        nullable= False
    )

    email = db.Column(
        db.String(255),
        unique = True,
        nullable = False
    )
    password_hash = db.Column(
        db.String(255),
        nullable = False
    )
    role = db.Column(
        db.String(20),
        nullable = False,
        default = "user"
    )
    
    @property
    def is_admin(self):
        return self.role == "admin"


# Project tables are defined in SQL_Setup.sql; these models map onto them.
class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="in progress")
    style_no = db.Column(db.String(100))
    po_no = db.Column(db.String(100))
    project_date = db.Column(db.Date)
    customer = db.Column(db.String(255))
    size_range = db.Column(db.String(50))
    season = db.Column(db.String(50))
    fabric_yarn = db.Column(db.String(100))
    designer = db.Column(db.String(100))
    weight = db.Column(db.String(100))
    description = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class ProjectColor(db.Model):
    __tablename__ = "project_colors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )


class ProjectMaterial(db.Model):
    __tablename__ = "project_materials"

    id = db.Column(db.Integer, primary_key=True)
    colorway_id = db.Column(
        db.Integer,
        db.ForeignKey("project_colors.id", ondelete="CASCADE"),
        nullable=False
    )
    name = db.Column(db.String(50))
    material = db.Column(db.String(100))
    supplier = db.Column(db.String(100))
    supplier_contact = db.Column(db.String(255))
    quantity = db.Column(db.Integer)
    location = db.Column(db.String(1000))
    article_no = db.Column(db.String(100))
    material_size = db.Column(db.String(50))
    uom = db.Column(db.String(10))
    color = db.Column(db.String(50))
    notes = db.Column(db.Text)

from .extensions import login_manager

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
