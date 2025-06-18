from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secure-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    subjects = db.relationship('Subject', backref='user', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    days_left = db.Column(db.Integer, nullable=False)
    total_units = db.Column(db.Integer, nullable=False)
    completed_units = db.Column(db.Integer, default=0)
    priority = db.Column(db.Integer, nullable=False)
    complexity = db.Column(db.Integer, nullable=False)

    @property
    def progress_percent(self):
        if self.total_units > 0:
            return round((self.completed_units / self.total_units) * 100, 1)
        return 0.0

    @property
    def priority_label(self):
        return {1: 'Highest', 2: 'High', 3: 'Medium', 4: 'Low', 5: 'Lowest'}.get(self.priority, 'Unknown')

    @property
    def complexity_label(self):
        return {1: 'Very Easy', 2: 'Easy', 3: 'Medium', 4: 'Hard', 5: 'Very Hard'}.get(self.complexity, 'Unknown')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))

        try:
            new_user = User(
                username=username,
                email=email,
                password=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)

@app.route('/subjects')
@login_required
def subjects():
    user_subjects = Subject.query.filter_by(user_id=current_user.id).all()
    return render_template('subjects.html', subjects=user_subjects)

@app.route('/add_subject', methods=['GET', 'POST'])
@login_required
def add_subject():
    if request.method == 'POST':
        try:
            new_subject = Subject(
                user_id=current_user.id,
                name=request.form.get('name'),
                days_left=request.form.get('days_left'),
                total_units=request.form.get('total_units'),
                priority=request.form.get('priority'),
                complexity=request.form.get('complexity')
            )
            db.session.add(new_subject)
            db.session.commit()
            flash('Subject added successfully!', 'success')
            return redirect(url_for('subjects'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding subject. Please check your inputs.', 'danger')
    return render_template('add_subject.html')

@app.route('/progress')
@login_required
def progress():
    return render_template('progress.html')

@app.route('/pomodoro')
@login_required
def pomodoro():
    return render_template('pomodoro.html')

@app.route('/timetable')
@login_required
def timetable():
    return render_template('timetable.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='127.0.0.1', port=5000, debug=True)