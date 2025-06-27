from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, time
from scheduler import generate_knapsack_schedule  # ⬅️ Import your scheduler
from flask_migrate import Migrate

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = '--'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------------------- Models ---------------------- #
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

class TimetableSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    subject = db.relationship('Subject')

class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    timetable_session_id = db.Column(db.Integer, db.ForeignKey('timetable_session.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    units_completed = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    subject = db.relationship('Subject')
    timetable_session = db.relationship('TimetableSession')

# ---------------------- Auth ---------------------- #
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
        except Exception:
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

# ---------------------- Pages ---------------------- #
@app.route('/dashboard')
@login_required
def dashboard():
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    overall_progress = round(
        sum(subject.progress_percent for subject in subjects) / len(subjects), 1
    ) if subjects else 0
    return render_template('dashboard.html', username=current_user.username, overall_progress=overall_progress)

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
        except Exception:
            db.session.rollback()
            flash('Error adding subject. Please check your inputs.', 'danger')
    return render_template('add_subject.html')

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
@login_required
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    if subject.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('subjects'))
    db.session.delete(subject)
    db.session.commit()
    flash("Subject deleted successfully.", "success")
    return redirect(url_for('subjects'))

@app.route('/progress')
@login_required
def progress():
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    overall_progress = round(
        sum(s.progress_percent for s in subjects) / len(subjects), 1
    ) if subjects else 0
    
    # Get recent study sessions for display
    recent_sessions = StudySession.query.filter_by(
        user_id=current_user.id, 
        is_completed=True
    ).order_by(StudySession.end_time.desc()).limit(10).all()
    
    return render_template("progress.html", subjects=subjects, overall_progress=overall_progress, recent_sessions=recent_sessions)

@app.route('/pomodoro')
@login_required
def pomodoro():
    return render_template('pomodoro.html')

@app.route('/pomodoro/<subject_name>')
@login_required
def pomodoro_subject(subject_name):
    return render_template('pomodoro.html', subject_name=subject_name)

# ---------------------- Study Session Management ---------------------- #
@app.route('/start_session/<int:timetable_session_id>', methods=['POST'])
@login_required
def start_session(timetable_session_id):
    timetable_session = TimetableSession.query.get_or_404(timetable_session_id)
    
    if timetable_session.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Check if session already started
    existing_session = StudySession.query.filter_by(
        timetable_session_id=timetable_session_id,
        is_completed=False
    ).first()
    
    if existing_session:
        return jsonify({'success': False, 'message': 'Session already in progress'}), 400
    
    # Create new study session
    study_session = StudySession(
        user_id=current_user.id,
        subject_id=timetable_session.subject_id,
        timetable_session_id=timetable_session_id,
        start_time=datetime.now()
    )
    
    db.session.add(study_session)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'session_id': study_session.id,
        'message': 'Study session started!'
    })

@app.route('/complete_session/<int:study_session_id>', methods=['POST'])
@login_required
def complete_session(study_session_id):
    study_session = StudySession.query.get_or_404(study_session_id)
    
    if study_session.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    if study_session.is_completed:
        return jsonify({'success': False, 'message': 'Session already completed'}), 400
    
    # Complete the session
    study_session.end_time = datetime.now()
    study_session.duration_minutes = int((study_session.end_time - study_session.start_time).total_seconds() / 60)
    study_session.is_completed = True
    
    # Calculate units completed based on duration and complexity
    # Base formula: 1 unit per 30 minutes, adjusted by complexity
    complexity_factor = {1: 1.5, 2: 1.25, 3: 1.0, 4: 0.75, 5: 0.5}
    base_units = study_session.duration_minutes / 30
    units_completed = max(1, int(base_units * complexity_factor.get(study_session.subject.complexity, 1.0)))
    
    study_session.units_completed = units_completed
    
    # Update subject progress
    subject = study_session.subject
    subject.completed_units = min(
        subject.completed_units + units_completed,
        subject.total_units
    )
    
    # Mark timetable session as completed
    study_session.timetable_session.is_completed = True
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'units_completed': units_completed,
        'total_progress': subject.progress_percent,
        'message': f'Great job! You completed {units_completed} units.'
    })

@app.route('/get_active_session')
@login_required
def get_active_session():
    """Get currently active study session for the user"""
    active_session = StudySession.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).first()
    
    if active_session:
        elapsed_minutes = int((datetime.now() - active_session.start_time).total_seconds() / 60)
        return jsonify({
            'has_active_session': True,
            'session_id': active_session.id,
            'subject_name': active_session.subject.name,
            'elapsed_minutes': elapsed_minutes,
            'planned_duration': active_session.timetable_session.duration
        })
    
    return jsonify({'has_active_session': False})

# ---------------------- Timetable ---------------------- #
@app.route('/timetable')
@login_required
def timetable():
    sessions = TimetableSession.query.filter_by(user_id=current_user.id).order_by(
        TimetableSession.date, TimetableSession.start_time
    ).all()
    return render_template('timetable.html', timetable=sessions)

@app.route('/generate_schedule', methods=['POST'])
@login_required
def generate_schedule():
    # Get all subjects for the current user
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    time_limit = 240

    # Call your fatigue-aware scheduler
    selected_sessions = generate_knapsack_schedule(subjects, time_limit)

    today = datetime.today().date()
    start_time = time(9, 0)  

    for session in selected_sessions:
        duration = session['duration']
        end_time = (datetime.combine(today, start_time) + timedelta(minutes=duration)).time()

        timetable_entry = TimetableSession(
            user_id=current_user.id,
            subject_id=session['subject'].id,
            date=today,
            start_time=start_time,
            end_time=end_time,
            duration=duration
        )
        db.session.add(timetable_entry)

        # Update start time for next session
        start_time = end_time

    db.session.commit()
    flash("Today's schedule generated successfully!", "success")
    return redirect(url_for('dashboard'))


@app.route('/generate_timetable')
@login_required
def generate_timetable():
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    if not subjects:
        flash("Add subjects before generating a timetable.", "warning")
        return redirect(url_for('subjects'))

    # Clear previous sessions
    TimetableSession.query.filter_by(user_id=current_user.id).delete()
    StudySession.query.filter_by(user_id=current_user.id).delete()

    start_date = datetime.now().date()
    max_days_left = max(subject.days_left for subject in subjects)

    for i in range(max_days_left):
        current_date = start_date + timedelta(days=i)
        current_time = time(9, 0)
        total_minutes = 6 * 60  # 6 hours/day = 360 minutes available

        # Generate daily schedule using knapsack
        daily_schedule = generate_knapsack_schedule(subjects, total_minutes)

        for item in daily_schedule:
            subject = item['subject']
            duration = item['duration']

            end_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=duration)).time()

            session = TimetableSession(
                user_id=current_user.id,
                subject_id=subject.id,
                date=current_date,
                start_time=current_time,
                end_time=end_time,
                duration=duration
            )
            db.session.add(session)

            # 15-minute break between sessions
            current_time = (datetime.combine(datetime.today(), end_time) + timedelta(minutes=15)).time()

    db.session.commit()
    flash("Timetable generated successfully for all days until your exams!", "success")
    return redirect(url_for('timetable'))

# ---------------------- Run ---------------------- #
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='127.0.0.1', port=5000, debug=True)