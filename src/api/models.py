from datetime import date

from flask_login import UserMixin
from .extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")

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

    colorways = db.relationship(
        "ProjectColor",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    measurement_points = db.relationship(
        "PointsMeasured",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    files = db.relationship(
        "ProjectFile",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectColor(db.Model):
    __tablename__ = "project_colors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)

    project = db.relationship("Project", back_populates="colorways")
    materials = db.relationship(
        "ProjectMaterial",
        back_populates="colorway",
        cascade="all, delete-orphan",
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
    import_source_file = db.Column(db.String(255))
    import_source_row = db.Column(db.Integer)
    import_field_sources = db.Column(db.Text)

    colorway = db.relationship("ProjectColor", back_populates="materials")


class PointsMeasured(db.Model):
    __tablename__ = "points_measured"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    code = db.Column(db.String(10))
    name = db.Column(db.String(100))
    tol = db.Column(db.String(10))
    sizes = db.Column(db.String(10))
    measure = db.Column(db.String(10))
    grade = db.Column(db.String(10))
    notes = db.Column(db.String(1000))

    project = db.relationship("Project", back_populates="measurement_points")


class ProjectFile(db.Model):
    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))
    file_type = db.Column(db.String(50))

    project = db.relationship("Project", back_populates="files")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
