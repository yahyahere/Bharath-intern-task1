import os
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename

from .models import db, User, Project, Assignment, Document


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'nexus.db')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

db.init_app(app)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.before_first_request
def create_tables():
    db.create_all()


@app.route('/')
@login_required
def dashboard():
    if current_user.role == 'Admin':
        projects = Project.query.all()
        users = User.query.all()
        return render_template('admin_dashboard.html', projects=projects, users=users)
    elif current_user.role == 'Lead':
        projects = Project.query.join(Assignment).filter(Assignment.user_id == current_user.id)
        return render_template('lead_dashboard.html', projects=projects)
    else:
        projects = Project.query.join(Assignment).filter(Assignment.user_id == current_user.id)
        return render_template('dev_dashboard.html', projects=projects)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/projects/add', methods=['GET', 'POST'])
@login_required
def add_project():
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form['name']
        desc = request.form['description']
        deadline = request.form['deadline']
        project = Project(name=name, description=desc, deadline=deadline)
        db.session.add(project)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_project.html')


@app.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    documents = Document.query.filter_by(project_id=project.id).all()
    assignments = Assignment.query.filter_by(project_id=project.id).all()
    return render_template('project_detail.html', project=project, documents=documents, assignments=assignments)


@app.route('/projects/<int:project_id>/complete')
@login_required
def mark_complete(project_id):
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
    project = Project.query.get_or_404(project_id)
    project.completed = True
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/assign/<int:project_id>', methods=['GET', 'POST'])
@login_required
def assign(project_id):
    if current_user.role not in ['Admin', 'Lead']:
        return redirect(url_for('dashboard'))
    project = Project.query.get_or_404(project_id)
    if request.method == 'POST':
        user_id = int(request.form['user_id'])
        assign = Assignment(user_id=user_id, project_id=project.id)
        db.session.add(assign)
        db.session.commit()
        return redirect(url_for('project_detail', project_id=project.id))
    users = User.query.all()
    return render_template('assign.html', project=project, users=users)


@app.route('/upload/<int:project_id>', methods=['GET', 'POST'])
@login_required
def upload(project_id):
    project = Project.query.get_or_404(project_id)
    if current_user.role not in ['Admin', 'Lead']:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            doc = Document(project_id=project.id, filename=filename, path=filepath)
            db.session.add(doc)
            db.session.commit()
            return redirect(url_for('project_detail', project_id=project.id))
    return render_template('upload.html', project=project)


@app.route('/docs/<filename>')
@login_required
def get_document(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password_hash=pw_hash, role=role)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_user.html')


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        if 'password' in request.form and request.form['password']:
            current_user.password_hash = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        if 'mfa' in request.form and request.form['mfa'] == 'enable':
            import pyotp
            secret = pyotp.random_base32()
            current_user.mfa_secret = secret
            flash(f"MFA enabled. Secret: {secret}")
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('settings.html')


if __name__ == '__main__':
    app.run(debug=True)
