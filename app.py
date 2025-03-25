from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from werkzeug.security import generate_password_hash


# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
from models import db, User, Task

db.init_app(app)  # FIX: Register the Flask app with SQLAlchemy

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', tasks=tasks)

from forms import RegisterForm

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

from forms import LoginForm
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


from datetime import datetime


@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form['title']
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'Medium')
    deadline_str = request.form.get('deadline', None)

    # ✅ Convert string to datetime
    deadline = datetime.strptime(deadline_str, '%Y-%m-%d') if deadline_str else None

    new_task = Task(
        title=title,
        description=description,
        priority=priority,
        deadline=deadline,  # ✅ Store as datetime
        user_id=current_user.id
    )

    db.session.add(new_task)
    db.session.commit()

    flash('Task added successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)

    # Ensure that the user can only edit their own tasks
    if task.user_id != current_user.id:
        flash("You don't have permission to edit this task.", 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form.get('description', '')
        task.priority = request.form.get('priority', 'Medium')
        deadline_str = request.form.get('deadline', None)

        if deadline_str:
            task.deadline = datetime.strptime(deadline_str, '%Y-%m-%d')

        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_task.html', task=task)

@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)

    # Ensure that the user can only delete their own tasks
    if task.user_id != current_user.id:
        flash("You don't have permission to delete this task.", 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # FIX: Ensure database tables are created
    app.run(debug=True)
