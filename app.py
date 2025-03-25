from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)


os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

from models import db, User, Task

db.init_app(app)

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
    if 'user_id' not in session:
        flash('Session expired. Please log in again.', 'warning')
        return redirect(url_for('login'))

    tasks = Task.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', tasks=tasks, username=session.get('username'))


from forms import RegisterForm


@app.route('/register', methods=['GET', 'POST'])
def register():
    session.pop('_flashes', None)

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
    if form.validate_on_submit():
        identifier = form.identifier.data
        password = form.password.data

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and user.password == password:
            login_user(user)
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form['title']
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'Medium')
    deadline_str = request.form.get('deadline', None)

    deadline = datetime.strptime(deadline_str, '%Y-%m-%d') if deadline_str else None

    new_task = Task(
        title=title,
        description=description,
        priority=priority,
        deadline=deadline,
        user_id=session['user_id']
    )

    db.session.add(new_task)
    db.session.commit()

    flash('Task added successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)

    if task.user_id != session['user_id']:
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

    if task.user_id != session['user_id']:
        flash("You don't have permission to delete this task.", 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
