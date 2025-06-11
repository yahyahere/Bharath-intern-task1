from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin


db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Developer')
    mfa_secret = db.Column(db.String(32))

    assignments = db.relationship('Assignment', back_populates='user')

    def __repr__(self):
        return f"<User {self.username}>"


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.String(20))
    completed = db.Column(db.Boolean, default=False)

    assignments = db.relationship('Assignment', back_populates='project')
    documents = db.relationship('Document', back_populates='project')

    def __repr__(self):
        return f"<Project {self.name}>"


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

    user = db.relationship('User', back_populates='assignments')
    project = db.relationship('Project', back_populates='assignments')


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    filename = db.Column(db.String(200))
    path = db.Column(db.String(200))

    project = db.relationship('Project', back_populates='documents')

