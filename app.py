import os
import json
import base64
import tempfile
import random
import string
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from dotenv import load_dotenv
from google import genai
from src.generate_paper import generate_paper
from src.utils import *
from pydantic import BaseModel
from typing import List

class GradingResult(BaseModel):
    question_number: int
    extracted_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str

class GradingResponse(BaseModel):
    results: List[GradingResult]

load_dotenv() # Load environment variables from .env file

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def get_api_key():
    # Prefer environment variable, otherwise read from `apikey.txt`
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key.strip()
    try:
        with open('apikey.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

api_key = get_api_key()
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not set and `apikey.txt` not found")

client = genai.Client(api_key=api_key)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'teacher' or 'student'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET'])
def login():
    # Redirect to the default (student) login page to avoid generic member login
    return redirect(url_for('login_role', role='student'))


@app.route('/login/<role>', methods=['GET', 'POST'])
def login_role(role):
    role = role.lower()
    if role not in ('teacher', 'student'):
        flash('Invalid login portal.', 'danger')
        return redirect(url_for('login_role', role='student'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if (user.role or 'student') != role:
                error = 'Please use the correct portal for your account.'
            else:
                session['username'] = username
                session['role'] = user.role
                flash('Login successful!', 'success')
                if user.role == 'teacher':
                    return redirect(url_for('teacher_portal'))
                else:
                    return redirect(url_for('student_portal'))
        else:
            error = 'Invalid username or password.'
    return render_template('login.html', error=error, role=role)

@app.route('/signup', methods=['GET'])
def signup():
    # Redirect to default (student) signup to avoid generic member signup
    return redirect(url_for('signup_role', role='student'))


@app.route('/signup/<role>', methods=['GET', 'POST'])
def signup_role(role):
    role = role.lower()
    if role not in ('teacher', 'student'):
        flash('Invalid signup portal.', 'danger')
        return redirect(url_for('signup_role', role='student'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            error = 'All fields are required.'
        elif User.query.filter_by(username=username).first():
            error = 'Username already exists.'
        else:
            new_user = User(username=username, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login_role', role=role))
    return render_template('signup.html', error=error, role=role)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Home page with options for different exam categories"""
    return render_template('index.html')

@app.route('/exam_selection/<exam_type>')
def exam_selection(exam_type):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    book_structure = get_available_books()
    return render_template('exam_selection.html', exam_type=exam_type, book_structure=book_structure)

@app.route('/generate_exam', methods=['POST'])
@login_required
def generate_exam():
    exam_mode = request.form.get('exam_mode')
    exam_name = request.form.get('exam_name')
    json_path = None

    if exam_name == 'SCHOOL':
        school_exam_type = request.form.get('school_exam_type')
        subject = request.form.get('subject')
        grade = request.form.get('grade')
        board = request.form.get('board')
        language = request.form.get('language')
        chapters = request.form.getlist('chapters')

        # Infer exam mode for School exams
        if school_exam_type == 'SCHOOL_QUIZ':
            exam_mode = 'online'
        else:
            exam_mode = 'offline'

        json_path = generate_paper(
            name_of_the_exam=school_exam_type,
            subject=subject,
            grade=grade,
            board=board,
            chapters=chapters,
            language=language
        )
        session['exam_name'] = school_exam_type
        session['subject'] = subject
        session['grade'] = grade
        session['board'] = board
        session['chapters'] = chapters
        session['language'] = language
    else:
        difficulty = request.form.get('difficulty')
        # For competitive exams, we now use exam_mode_selection to determine online/offline
        exam_mode_selection = request.form.get('exam_mode_selection')
        
        # Default to MCQ for competitive exams
        exam_format = 'MCQ'
        
        if exam_mode_selection == 'ONLINE':
            exam_mode = 'online'
        else:
            exam_mode = 'offline'

        json_path = generate_paper(
            name_of_the_exam=exam_name, 
            difficulty_level=difficulty, 
            format_of_the_exam=exam_format
        )
        session['exam_name'] = exam_name
        session['difficulty'] = difficulty
        session['exam_format'] = exam_format

    session['json_path'] = json_path
    # Initialize answers_uploaded to False when a new exam is generated
    session['answers_uploaded'] = False
    
    if not json_path:
        flash('Could not generate the exam. Please check your inputs.', 'danger')
        return redirect(url_for('exam_selection', exam_type=exam_name))

    if exam_mode == 'online':
        return redirect(url_for('online_exam'))
    else:  # offline
        return redirect(url_for('offline_exam'))

@app.route('/online_exam')
@login_required
def online_exam():
    """Display online exam with questions and options"""
    json_path = session.get('json_path')
    
    if not json_path or not os.path.exists(json_path):
        flash('Exam session not found or expired. Please start a new exam.', 'warning')
        return redirect(url_for('index'))
    
    with open(json_path, 'r') as f:
        questions = json.load(f)
    
    return render_template('online_exam.html', questions=questions)

@app.route('/submit_exam', methods=['POST'])
@login_required
def submit_exam():
    """Handle exam submission and calculate score; also store classroom assignment submissions if applicable."""
    json_path = session.get('json_path')
    
    if not json_path or not os.path.exists(json_path):
        flash('Exam session not found or expired. Please start a new exam.', 'warning')
        return redirect(url_for('index'))
    
    with open(json_path, 'r') as f:
        questions = json.load(f)
    
    user_answers = {}
    for q in questions:
        q_id = str(q['question_number'])
        user_answers[q_id] = request.form.get(q_id, '')
    
    score = 0
    total = len(questions)
    results = []
    
    for q in questions:
        q_id = str(q['question_number'])
        user_answer = user_answers.get(q_id, '')
        correct_answer = q['answer']
        
        is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
        if is_correct:
            score += 1
        
        results.append({
            'question_number': q['question_number'],
            'question': q['question'],
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'solution': q.get('solution', '')
        })
    
    percentage = (score / total) * 100 if total > 0 else 0

    # Persist assignment submission if in classroom assignment context
    assignment_id = session.get('assignment_id')
    if assignment_id:
        try:
            user = get_current_user()
            assignment = Assignment.query.get(assignment_id)
            now = datetime.now()
            # Enforce opens/due at submission
            if assignment:
                if assignment.opens_at and now < assignment.opens_at:
                    session.pop('assignment_id', None)
                    flash('This assignment is not open yet.', 'warning')
                    return redirect(url_for('classroom_view', class_id=assignment.classroom_id))
                if assignment.due_at and now > assignment.due_at and (assignment.late_policy or 'allow') == 'block':
                    session.pop('assignment_id', None)
                    flash('This assignment is closed. Submission not accepted.', 'danger')
                    return redirect(url_for('classroom_view', class_id=assignment.classroom_id))
            details = {'results': results}
            existing = AssignmentSubmission.query.filter_by(assignment_id=assignment_id, user_id=user.id).first()
            is_late = bool(assignment and assignment.due_at and now > assignment.due_at and (assignment.late_policy or 'allow') != 'block')
            if existing:
                existing.score = score
                existing.total = total
                existing.percentage = percentage
                existing.details_json = json.dumps(details)
                existing.is_late = is_late
                existing.submitted_at = datetime.utcnow()
            else:
                sub = AssignmentSubmission(
                    assignment_id=assignment_id,
                    user_id=user.id,
                    score=score,
                    total=total,
                    percentage=percentage,
                    details_json=json.dumps(details),
                    is_late=is_late
                )
                db.session.add(sub)
            db.session.commit()
        except Exception as e:
            # Don't break user flow if DB write fails
            app.logger.error(f"Failed to store assignment submission: {e}")
        finally:
            session.pop('assignment_id', None)
    
    return render_template('results.html', 
                          results=results, 
                          score=score, 
                          total=total, 
                          percentage=percentage)

@app.route('/offline_exam')
@login_required
def offline_exam():
    """Generate and provide downloadable exam paper"""
    json_path = session.get('json_path')
    
    if not json_path or not os.path.exists(json_path):
        flash('Exam session not found or expired. Please start a new exam.', 'warning')
        return redirect(url_for('index'))
    
    with open(json_path, 'r') as f:
        questions = json.load(f)
    
    answers_uploaded = session.get('answers_uploaded', False)
    
    return render_template('offline_exam.html', 
                          questions=questions, 
                          json_path=json_path,
                          answers_uploaded=answers_uploaded)

@app.route('/download_question_paper')
@login_required
def download_question_paper():
    """Download the generated question paper as PDF"""
    json_path = session.get('json_path')
    
    if not json_path or not os.path.exists(json_path):
        flash('Exam session not found or expired. Please start a new exam.', 'warning')
        return redirect(url_for('index'))
    
    question_pdf_path, _ = extract_and_convert(json_path)
    
    if question_pdf_path and os.path.exists(question_pdf_path):
        return send_file(question_pdf_path, as_attachment=True, download_name='question_paper.pdf')
    else:
        flash('Could not generate question paper PDF.', 'danger')
        return redirect(url_for('offline_exam'))

@app.route('/download_answer_sheet')
@login_required
def download_answer_sheet():
    """Download the generated answer sheet as PDF"""
    json_path = session.get('json_path')
    
    if not json_path or not os.path.exists(json_path):
        flash('Exam session not found or expired. Please start a new exam.', 'warning')
        return redirect(url_for('index'))
    
    # Only allow download if answers have been uploaded
    if not session.get('answers_uploaded'):
        flash('Please upload your answers first to download the answer sheet.', 'warning')
        return redirect(url_for('offline_exam'))

    _, answer_pdf_path = extract_and_convert(json_path)
    
    if answer_pdf_path and os.path.exists(answer_pdf_path):
        return send_file(answer_pdf_path, as_attachment=True, download_name='answer_sheet.pdf')
    else:
        flash('Could not generate answer sheet PDF.', 'danger')
        return redirect(url_for('offline_exam'))

@app.route('/upload_answers', methods=['GET', 'POST'])
@login_required
def upload_answers():
    """Handle upload of answer images/PDFs and process them with Gemini"""
    if request.method == 'POST':
        if 'answer_file' not in request.files:
            return render_template('upload_answers.html', error="No file part")
        
        file = request.files['answer_file']
        
        if file.filename == '':
            return render_template('upload_answers.html', error="No selected file")
        
        if file and allowed_file(file.filename):
            temp_dir = tempfile.mkdtemp()
            filepath = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(filepath)
            
            try:
                json_path = session.get('json_path')
                with open(json_path, 'r') as f:
                    questions = json.load(f)
                
                # Prepare content for Gemini
                prompt = f"""
                I have an exam with the following questions and correct answers:
                {json.dumps([{'question_number': q['question_number'], 'question': q['question'], 'answer': q['answer']} for q in questions], indent=2)}
                
                The attached file contains the student's handwritten or typed answers.
                Your task is to:
                1. Extract the student's answer for each question.
                2. Compare it with the correct answer.
                3. Determine if the answer is correct (or partially correct for subjective questions).
                4. Assign a score (1 for correct, 0 for incorrect).
                
                Return a JSON array with the structure:
                [ {{"question_number": 1, "extracted_answer": "...", "correct_answer": "...", "is_correct": true/false, "explanation": "..."}} ]
                
                If you can't find an answer for a question, mark it as incorrect.
                """
                
                contents = [prompt]
                
                # Check file type and prepare accordingly
                mime_type = mimetypes.guess_type(filepath)[0]
                
                if mime_type == 'application/pdf':
                     # Upload PDF to Gemini
                    uploaded_file = client.files.upload(file=filepath)
                    contents.append(uploaded_file)
                else:
                    # Handle Image
                    with open(filepath, "rb") as img_file:
                        image_bytes = img_file.read()
                    
                    image_parts = {
                        "mime_type": mime_type if mime_type else "image/jpeg",
                        "data": base64.b64encode(image_bytes).decode('utf-8')
                    }
                    contents.append(image_parts)
                
                # Use a capable model with structured output
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=contents,
                    config={
                        'response_mime_type': 'application/json',
                        'response_schema': GradingResponse
                    }
                )

                try:
                    # Parse the response using Pydantic
                    grading_response = response.parsed
                    results = [result.model_dump() for result in grading_response.results]
                    
                    score = sum(1 for r in results if r.get('is_correct', False))
                    total = len(results)
                    percentage = (score / total) * 100 if total > 0 else 0

                    session['answers_uploaded'] = True
                    
                    return render_template('results.html', 
                                          results=results, 
                                          score=score, 
                                          total=total, 
                                          percentage=percentage,
                                          is_uploaded=True)
                except Exception as e:
                    return render_template('upload_answers.html', 
                                          error=f"Error parsing AI response: {str(e)}",
                                          response_text=response.text)
            
            except Exception as e:
                return render_template('upload_answers.html', error=f"Error processing file: {str(e)}")
            
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
        
        else:
            return render_template('upload_answers.html', 
                                  error="File type not allowed. Please upload a PDF, JPG, JPEG, or PNG.")
    
    return render_template('upload_answers.html')

# ----------------------
# Classroom feature models and helpers
# ----------------------

ALLOWED_MATERIAL_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}


def allowed_material_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MATERIAL_EXTENSIONS


class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ClassroomMembership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), default='student')  # 'teacher' or 'student'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('classroom_id', 'user_id', name='uq_class_user'),)


class ClassPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)
    attachment_path = db.Column(db.String(255), nullable=True)
    post_type = db.Column(db.String(20), default='post')  # 'post', 'chat', 'material'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PostReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('class_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PostComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('class_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CommentReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('post_comment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    json_path = db.Column(db.String(255), nullable=False)
    config_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    opens_at = db.Column(db.DateTime, nullable=True)
    due_at = db.Column(db.DateTime, nullable=True)
    late_policy = db.Column(db.String(20), nullable=False, default='allow')  # 'allow' or 'block'


class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    details_json = db.Column(db.Text, nullable=True)
    is_late = db.Column(db.Boolean, nullable=False, default=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('assignment_id', 'user_id', name='uq_assignment_user'),)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    payload_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)

# Helper utilities

def get_current_user():
    username = session.get('username')
    if not username:
        return None
    return User.query.filter_by(username=username).first()


def require_membership(classroom_id):
    user = get_current_user()
    if not user:
        return None, None, redirect(url_for('login'))
    classroom = Classroom.query.get_or_404(classroom_id)
    membership = ClassroomMembership.query.filter_by(classroom_id=classroom.id, user_id=user.id).first()
    if not membership:
        flash('You are not a member of this classroom.', 'danger')
        return None, None, redirect(url_for('classrooms'))
    return classroom, membership, None


# ----------------------
# In-app notifications utilities & routes
# ----------------------

@app.context_processor
def inject_unread_notifications():
    try:
        user = get_current_user()
        if not user:
            return dict(unread_notifications=0)
        count = Notification.query.filter_by(user_id=user.id, read_at=None).count()
        return dict(unread_notifications=count)
    except Exception:
        return dict(unread_notifications=0)

@app.route('/notifications')
@login_required
def notifications_page():
    user = get_current_user()
    notifs = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    # Attempt to parse payload for convenience
    parsed = []
    for n in notifs:
        payload = None
        if n.payload_json:
            try:
                payload = json.loads(n.payload_json)
            except Exception:
                payload = None
        parsed.append({'obj': n, 'payload': payload})
    return render_template('notifications.html', notifications=parsed)

@app.route('/notifications/<int:notif_id>/read')
@login_required
def mark_notification_read(notif_id):
    user = get_current_user()
    n = Notification.query.get_or_404(notif_id)
    if n.user_id != user.id:
        flash('Not authorized to modify this notification.', 'danger')
        return redirect(url_for('notifications_page'))
    if not n.read_at:
        n.read_at = datetime.utcnow()
        db.session.commit()
    return redirect(url_for('notifications_page'))

@app.route('/notifications/mark_all_read')
@login_required
def mark_all_notifications_read():
    user = get_current_user()
    Notification.query.filter_by(user_id=user.id, read_at=None).update({'read_at': datetime.utcnow()})
    db.session.commit()
    return redirect(url_for('notifications_page'))

# ----------------------
# Role-specific portals
# ----------------------

@app.route('/portal/teacher')
@login_required
def teacher_portal():
    if session.get('role') != 'teacher':
        flash('Only teachers can access the Teacher Portal.', 'danger')
        return redirect(url_for('index'))
    user = get_current_user()
    owned_classes = Classroom.query.filter_by(owner_id=user.id).order_by(Classroom.created_at.desc()).all()
    teacher_memberships = ClassroomMembership.query.filter_by(user_id=user.id, role='teacher').all()
    extra_ids = [m.classroom_id for m in teacher_memberships if m.classroom_id not in [c.id for c in owned_classes]]
    extra_classes = Classroom.query.filter(Classroom.id.in_(extra_ids)).all() if extra_ids else []
    classes = owned_classes + extra_classes
    return render_template('teacher_portal.html', classes=classes)


@app.route('/portal/student')
@login_required
def student_portal():
    if session.get('role') != 'student':
        flash('Only students can access the Student Portal.', 'danger')
        return redirect(url_for('index'))
    user = get_current_user()
    my_memberships = ClassroomMembership.query.filter_by(user_id=user.id).all()
    class_ids = [m.classroom_id for m in my_memberships]
    my_classes = Classroom.query.filter(Classroom.id.in_(class_ids)).order_by(Classroom.created_at.desc()).all() if class_ids else []
    return render_template('student_portal.html', classes=my_classes)

# ----------------------
# Classroom routes
# ----------------------

@app.route('/classrooms')
@login_required
def classrooms():
    user = get_current_user()
    my_memberships = ClassroomMembership.query.filter_by(user_id=user.id).all()
    class_ids = [m.classroom_id for m in my_memberships]
    my_classes = Classroom.query.filter(Classroom.id.in_(class_ids)).all() if class_ids else []
    return render_template('classrooms.html', classes=my_classes)


@app.route('/classrooms/create', methods=['POST'])
@login_required
def create_classroom():
    user = get_current_user()
    if session.get('role') != 'teacher':
        flash('Only teachers can create classrooms.', 'danger')
        return redirect(url_for('classrooms'))
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    if not name:
        flash('Class name is required.', 'warning')
        return redirect(url_for('classrooms'))
    # Generate unique code
    for _ in range(10):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Classroom.query.filter_by(code=code).first():
            break
    classroom = Classroom(name=name, description=description, owner_id=user.id, code=code)
    db.session.add(classroom)
    db.session.commit()
    # Add teacher membership
    db.session.add(ClassroomMembership(classroom_id=classroom.id, user_id=user.id, role='teacher'))
    db.session.commit()
    flash(f'Classroom created. Share code: {classroom.code}', 'success')
    return redirect(url_for('classroom_view', class_id=classroom.id))


@app.route('/classrooms/join', methods=['POST'])
@login_required
def join_classroom():
    user = get_current_user()
    if session.get('role') != 'student':
        flash('Only students can join classrooms with a code.', 'danger')
        return redirect(url_for('classrooms'))
    code = request.form.get('code', '').upper().strip()
    classroom = Classroom.query.filter_by(code=code).first()
    if not classroom:
        flash('Invalid classroom code.', 'danger')
        return redirect(url_for('classrooms'))
    existing = ClassroomMembership.query.filter_by(classroom_id=classroom.id, user_id=user.id).first()
    if existing:
        flash('You are already a member of this classroom.', 'info')
        return redirect(url_for('classroom_view', class_id=classroom.id))
    db.session.add(ClassroomMembership(classroom_id=classroom.id, user_id=user.id, role='student'))
    db.session.commit()
    flash(f'Joined classroom {classroom.name}', 'success')
    return redirect(url_for('classroom_view', class_id=classroom.id))


@app.route('/classroom/<int:class_id>')
@login_required
def classroom_view(class_id):
    classroom, membership, redirect_resp = require_membership(class_id)
    if redirect_resp:
        return redirect_resp
    posts_query = ClassPost.query.filter_by(classroom_id=classroom.id).order_by(ClassPost.created_at.desc()).all()
    assignments = Assignment.query.filter_by(classroom_id=classroom.id).order_by(Assignment.created_at.desc()).all()
    is_teacher = membership.role == 'teacher'

    user = get_current_user()
    now = datetime.now()

    post_ids = [p.id for p in posts_query]
    reactions = PostReaction.query.filter(PostReaction.post_id.in_(post_ids)).all() if post_ids else []
    comments = PostComment.query.filter(PostComment.post_id.in_(post_ids)).order_by(PostComment.created_at.asc()).all() if post_ids else []
    comment_ids = [c.id for c in comments]
    comment_reactions = CommentReaction.query.filter(CommentReaction.comment_id.in_(comment_ids)).all() if comment_ids else []
    user_ids = set([r.user_id for r in reactions]) | set([c.user_id for c in comments]) | set([cr.user_id for cr in comment_reactions]) | set([p.user_id for p in posts_query])
    users = User.query.filter(User.id.in_(list(user_ids))).all() if user_ids else []
    user_map = {u.id: u for u in users}

    reactions_by_post = {}
    for r in reactions:
        if r.post_id not in reactions_by_post:
            reactions_by_post[r.post_id] = []
        reactions_by_post[r.post_id].append(r)

    comments_by_post = {}
    for c in comments:
        if c.post_id not in comments_by_post:
            comments_by_post[c.post_id] = []
        comments_by_post[c.post_id].append(c)

    reactions_by_comment = {}
    for cr in comment_reactions:
        if cr.comment_id not in reactions_by_comment:
            reactions_by_comment[cr.comment_id] = []
        reactions_by_comment[cr.comment_id].append(cr)

    posts = []
    for p in posts_query:
        post_reactions = reactions_by_post.get(p.id, [])
        post_comments_query = comments_by_post.get(p.id, [])
        
        structured_comments = []
        for c in post_comments_query:
            comment_reacts = reactions_by_comment.get(c.id, [])
            structured_comments.append({
                'obj': c,
                'user': user_map.get(c.user_id),
                'reactions': comment_reacts
            })

        posts.append({
            'obj': p,
            'user': user_map.get(p.user_id),
            'reactions': post_reactions,
            'comments': structured_comments
        })

    subs_map = {}
    if membership.role == 'student' and assignments:
        aid_list = [a.id for a in assignments]
        subs = AssignmentSubmission.query.filter(AssignmentSubmission.assignment_id.in_(aid_list), AssignmentSubmission.user_id == user.id).all()
        subs_map = {s.assignment_id: s for s in subs}
        try:
            existing_due_notifs = Notification.query.filter_by(user_id=user.id, type='due_soon').all()
            existing_ids = set()
            for n in existing_due_notifs:
                if n.payload_json:
                    try:
                        payload = json.loads(n.payload_json)
                        if isinstance(payload, dict) and 'assignment_id' in payload:
                            existing_ids.add(int(payload['assignment_id']))
                    except Exception:
                        pass
            for a in assignments:
                if a.due_at and now < a.due_at and (a.due_at - now).total_seconds() <= 24*3600 and a.id not in subs_map and a.id not in existing_ids:
                    payload = {'class_id': class_id, 'assignment_id': a.id, 'title': a.title, 'due_at': a.due_at.isoformat()}
                    db.session.add(Notification(user_id=user.id, type='due_soon', payload_json=json.dumps(payload)))
            db.session.commit()
        except Exception as e:
            app.logger.error(f'Failed generating due reminders: {e}')

    return render_template('classroom.html', classroom=classroom, posts=posts, assignments=assignments, is_teacher=is_teacher, now=now, subs_map=subs_map, user_map=user_map, current_user=user)


@app.route('/classroom/<int:class_id>/post/<int:post_id>/react', methods=['POST'])
@login_required
def react_to_post(class_id, post_id):
    classroom, membership, redirect_resp = require_membership(class_id)
    if redirect_resp:
        return redirect_resp
    
    user = get_current_user()
    reaction_type = request.form.get('reaction_type')
    
    if not reaction_type:
        flash('Reaction type is required.', 'warning')
        return redirect(url_for('classroom_view', class_id=class_id))

    post = ClassPost.query.get_or_404(post_id)
    if post.classroom_id != class_id:
        flash('Invalid post.', 'danger')
        return redirect(url_for('classroom_view', class_id=class_id))

    existing_reaction = PostReaction.query.filter_by(post_id=post_id, user_id=user.id).first()
    
    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            db.session.delete(existing_reaction)
            flash('Reaction removed.', 'info')
        else:
            existing_reaction.reaction_type = reaction_type
            flash('Reaction updated.', 'success')
    else:
        new_reaction = PostReaction(post_id=post_id, user_id=user.id, reaction_type=reaction_type)
        db.session.add(new_reaction)
        flash('Reaction added.', 'success')
        
    db.session.commit()
    return redirect(url_for('classroom_view', class_id=class_id))


@app.route('/classroom/<int:class_id>/post/<int:post_id>/comment', methods=['POST'])
@login_required
def comment_on_post(class_id, post_id):
    classroom, membership, redirect_resp = require_membership(class_id)
    if redirect_resp:
        return redirect_resp

    user = get_current_user()
    content = request.form.get('content', '').strip()

    if not content:
        flash('Comment cannot be empty.', 'warning')
        return redirect(url_for('classroom_view', class_id=class_id))

    post = ClassPost.query.get_or_404(post_id)
    if post.classroom_id != class_id:
        flash('Invalid post.', 'danger')
        return redirect(url_for('classroom_view', class_id=class_id))

    new_comment = PostComment(post_id=post_id, user_id=user.id, content=content)
    db.session.add(new_comment)
    db.session.commit()
    
    flash('Comment added.', 'success')
    return redirect(url_for('classroom_view', class_id=class_id))


@app.route('/classroom/<int:class_id>/post', methods=['POST'])
@login_required
def classroom_post(class_id):
    classroom, membership, redirect_resp = require_membership(class_id)
    if redirect_resp:
        return redirect_resp
    # Only teachers can post to the stream
    if membership.role != 'teacher':
        flash('Only teachers can post to the class stream. Students can comment or react on posts, and submit assignments.', 'danger')
        return redirect(url_for('classroom_view', class_id=class_id))
    user = get_current_user()
    content = request.form.get('content', '').strip()
    post_type = request.form.get('post_type', 'post')
    attachment_path = None
    if 'material_file' in request.files:
        file = request.files['material_file']
        if file and file.filename:
            if not allowed_material_file(file.filename):
                flash('File type not allowed for materials.', 'warning')
                return redirect(url_for('classroom_view', class_id=class_id))
            filename = secure_filename(file.filename)
            upload_dir = os.path.join('static', 'uploads', f'class_{class_id}')
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)
            attachment_path = '/' + save_path.replace('\\', '/')
            if not content:
                content = f'Uploaded file: {filename}'
            post_type = 'material'
    if not content and not attachment_path:
        flash('Post content cannot be empty.', 'warning')
        return redirect(url_for('classroom_view', class_id=class_id))
    post = ClassPost(classroom_id=class_id, user_id=user.id, content=content, attachment_path=attachment_path, post_type=post_type)
    db.session.add(post)
    db.session.commit()
    flash('Posted to class stream.', 'success')
    return redirect(url_for('classroom_view', class_id=class_id))


@app.route('/classroom/<int:class_id>/assignments/create', methods=['POST'])
@login_required
def create_assignment(class_id):
    classroom, membership, redirect_resp = require_membership(class_id)
    if redirect_resp:
        return redirect_resp
    if membership.role != 'teacher':
        flash('Only teachers can create assignments.', 'danger')
        return redirect(url_for('classroom_view', class_id=class_id))
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    if not title:
        flash('Title is required.', 'warning')
        return redirect(url_for('classroom_view', class_id=class_id))
    # Determine exam config from form (reuse minimal fields)
    exam_name = request.form.get('exam_name')
    config = {}
    if exam_name == 'SCHOOL':
        school_exam_type = request.form.get('school_exam_type')
        subject = request.form.get('subject')
        grade = request.form.get('grade')
        board = request.form.get('board')
        chapters_str = request.form.get('chapters')
        chapters = [c.strip() for c in chapters_str.split(',')] if chapters_str else []
        json_path = generate_paper(
            name_of_the_exam=school_exam_type,
            subject=subject,
            grade=grade,
            board=board,
            chapters=chapters
        )
        config = {
            'exam_name': school_exam_type,
            'subject': subject,
            'grade': grade,
            'board': board,
            'chapters': chapters
        }
    else:
        difficulty = request.form.get('difficulty')
        exam_format = request.form.get('exam_format')
        json_path = generate_paper(
            name_of_the_exam=exam_name,
            difficulty_level=difficulty,
            format_of_the_exam=exam_format
        )
        config = {
            'exam_name': exam_name,
            'difficulty': difficulty,
            'exam_format': exam_format
        }
    if not json_path:
        flash('Failed to generate paper for assignment.', 'danger')
        return redirect(url_for('classroom_view', class_id=class_id))
    # Deadlines
    opens_at_str = request.form.get('opens_at', '').strip()
    due_at_str = request.form.get('due_at', '').strip()
    late_policy = (request.form.get('late_policy') or 'allow').strip().lower()
    def parse_dt(val):
        try:
            return datetime.strptime(val, '%Y-%m-%dT%H:%M') if val else None
        except Exception:
            return None
    opens_at = parse_dt(opens_at_str)
    due_at = parse_dt(due_at_str)

    assignment = Assignment(classroom_id=class_id, title=title, description=description, json_path=json_path, config_json=json.dumps(config), opens_at=opens_at, due_at=due_at, late_policy=late_policy)
    db.session.add(assignment)
    db.session.commit()

    # Notify students about new assignment
    try:
        student_mems = ClassroomMembership.query.filter_by(classroom_id=class_id, role='student').all()
        payload = {
            'class_id': class_id,
            'assignment_id': assignment.id,
            'title': title,
            'due_at': due_at.isoformat() if due_at else None
        }
        for m in student_mems:
            db.session.add(Notification(user_id=m.user_id, type='assignment_created', payload_json=json.dumps(payload)))
        db.session.commit()
    except Exception as e:
        app.logger.error(f'Failed to create assignment notifications: {e}')

    flash('Assignment created successfully.', 'success')
    return redirect(url_for('classroom_view', class_id=class_id))


@app.route('/classroom/<int:class_id>/assignments/<int:assignment_id>/start')
@login_required
def start_assignment(class_id, assignment_id):
    classroom, membership, redirect_resp = require_membership(class_id)
    if redirect_resp:
        return redirect_resp
    assignment = Assignment.query.filter_by(id=assignment_id, classroom_id=class_id).first_or_404()

    # Enforce open/close windows
    now = datetime.now()
    if assignment.opens_at and now < assignment.opens_at:
        flash('This assignment is not open yet.', 'warning')
        return redirect(url_for('classroom_view', class_id=class_id))
    if assignment.due_at and now > assignment.due_at and (assignment.late_policy or 'allow') == 'block':
        flash('This assignment is closed.', 'warning')
        return redirect(url_for('classroom_view', class_id=class_id))

    session['json_path'] = assignment.json_path
    session['assignment_id'] = assignment.id
    session['answers_uploaded'] = False
    session['late_start'] = bool(assignment.due_at and now > assignment.due_at and (assignment.late_policy or 'allow') != 'block')
    return redirect(url_for('online_exam'))


@app.route('/classroom/<int:class_id>/assignments/<int:assignment_id>/submissions')
@login_required
def view_submissions(class_id, assignment_id):
    classroom, membership, redirect_resp = require_membership(class_id)
    if redirect_resp:
        return redirect_resp
    if membership.role != 'teacher':
        flash('Only teachers can view submissions.', 'danger')
        return redirect(url_for('classroom_view', class_id=class_id))
    assignment = Assignment.query.filter_by(id=assignment_id, classroom_id=class_id).first_or_404()
    subs = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).order_by(AssignmentSubmission.submitted_at.desc()).all()
    # Map user ids to usernames
    user_map = {u.id: u.username for u in User.query.filter(User.id.in_([s.user_id for s in subs])).all()} if subs else {}
    return render_template('submissions.html', classroom=classroom, assignment=assignment, submissions=subs, user_map=user_map)




# ----------------------
# Classroom gradebook & analytics (teacher-only)
# ----------------------

@app.route('/classroom/<int:class_id>/students')
@login_required
def classroom_students(class_id):
    classroom, membership, redirect_resp = require_membership(class_id)
    if redirect_resp:
        return redirect_resp
    if membership.role != 'teacher':
        flash('Only teachers can view the student roster and grades.', 'danger')
        return redirect(url_for('classroom_view', class_id=class_id))

    # Get all assignments in this classroom
    assignments = Assignment.query.filter_by(classroom_id=class_id).order_by(Assignment.created_at.asc()).all()
    assignment_ids = [a.id for a in assignments]

    # Get all student memberships
    student_mems = ClassroomMembership.query.filter_by(classroom_id=class_id, role='student').all()
    student_ids = [m.user_id for m in student_mems]
    users = User.query.filter(User.id.in_(student_ids)).all() if student_ids else []
    user_map = {u.id: u for u in users}

    students_info = []
    for sid in student_ids:
        subs = AssignmentSubmission.query.filter(AssignmentSubmission.assignment_id.in_(assignment_ids), AssignmentSubmission.user_id == sid).order_by(AssignmentSubmission.submitted_at.asc()).all() if assignment_ids else []
        avg = round(sum(s.percentage for s in subs) / len(subs), 1) if subs else None
        last_time = subs[-1].submitted_at if subs else None
        students_info.append({
            'id': sid,
            'username': user_map[sid].username if sid in user_map else sid,
            'submissions_count': len(subs),
            'avg_percentage': avg,
            'last_submitted_at': last_time,
            'missing_count': max(len(assignments) - len(subs), 0)
        })

    # Sort by username
    students_info.sort(key=lambda x: x['username'])

    return render_template('students.html', classroom=classroom, assignments=assignments, students=students_info)


@app.route('/classroom/<int:class_id>/students/<int:student_id>')
@login_required
def student_report(class_id, student_id):
    classroom, membership, redirect_resp = require_membership(class_id)
    if redirect_resp:
        return redirect_resp
    if membership.role != 'teacher':
        flash('Only teachers can view student report cards.', 'danger')
        return redirect(url_for('classroom_view', class_id=class_id))

    # Ensure the target user is in this classroom
    student_mem = ClassroomMembership.query.filter_by(classroom_id=class_id, user_id=student_id).first()
    student_user = User.query.get_or_404(student_id)
    if not student_mem:
        flash('Selected student is not part of this classroom.', 'warning')
        return redirect(url_for('classroom_students', class_id=class_id))

    assignments = Assignment.query.filter_by(classroom_id=class_id).order_by(Assignment.created_at.asc()).all()
    assignment_ids = [a.id for a in assignments]
    subs = AssignmentSubmission.query.filter(AssignmentSubmission.assignment_id.in_(assignment_ids), AssignmentSubmission.user_id == student_id).all() if assignment_ids else []
    subs_by_aid = {s.assignment_id: s for s in subs}

    rows = []
    labels = []
    values = []
    for a in assignments:
        s = subs_by_aid.get(a.id)
        rows.append({
            'assignment': a,
            'submission': s
        })
        labels.append(a.title)
        values.append(round(s.percentage, 1) if s else None)

    completed_values = [v for v in values if v is not None]
    avg = round(sum(completed_values) / len(completed_values), 1) if completed_values else None
    best = max(completed_values) if completed_values else None
    worst = min(completed_values) if completed_values else None
    trend = None
    if len(completed_values) >= 2:
        trend = 'improving' if completed_values[-1] > completed_values[0] else ('declining' if completed_values[-1] < completed_values[0] else 'stable')

    analysis_parts = []
    if avg is not None:
        if avg >= 85:
            analysis_parts.append('Overall performance is excellent.')
        elif avg >= 70:
            analysis_parts.append('Overall performance is good, with room for improvement.')
        elif avg >= 50:
            analysis_parts.append('Performance is average; consistent practice recommended.')
        else:
            analysis_parts.append('Performance is below expectations; targeted support advised.')
    if trend:
        analysis_parts.append(f'Recent trend appears {trend}.')
    if best is not None and worst is not None and best - worst >= 20:
        analysis_parts.append('Scores vary significantly; focus on consistency.')
    analysis_text = ' '.join(analysis_parts) if analysis_parts else 'No sufficient data for analysis yet.'

    return render_template('student_report.html', classroom=classroom, student=student_user, rows=rows, avg=avg, best=best, worst=worst, labels=labels, values=values, analysis_text=analysis_text)


@app.route('/submissions/<int:submission_id>/update', methods=['POST'])
@login_required
def update_submission(submission_id):
    # Find submission and ensure current user is a teacher of the classroom
    sub = AssignmentSubmission.query.get_or_404(submission_id)
    assignment = Assignment.query.get_or_404(sub.assignment_id)
    classroom, membership, redirect_resp = require_membership(assignment.classroom_id)
    if redirect_resp:
        return redirect_resp
    if membership.role != 'teacher':
        flash('Only teachers can edit marks.', 'danger')
        return redirect(url_for('classroom_view', class_id=assignment.classroom_id))

    try:
        score = int(request.form.get('score', '').strip())
        total = int(request.form.get('total', '').strip())
        if total <= 0 or score < 0 or score > total:
            raise ValueError('Invalid score/total values.')
    except Exception:
        flash('Please provide valid numeric values for score and total (score <= total, total > 0).', 'warning')
        return redirect(url_for('student_report', class_id=assignment.classroom_id, student_id=sub.user_id))

    sub.score = score
    sub.total = total
    sub.percentage = (score / total) * 100.0
    sub.submitted_at = datetime.utcnow()  # update timestamp to reflect grade change
    db.session.commit()
    flash('Marks updated successfully.', 'success')
    return redirect(url_for('student_report', class_id=assignment.classroom_id, student_id=sub.user_id))


# Utility to ensure 'role' column exists for existing DBs without migrations

def ensure_user_role_column():
    try:
        # Ensure the user table exists before attempting to alter it
        tbl = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='user'"))
        if not tbl.fetchone():
            return
        # SQLite pragma to list columns
        res = db.session.execute(db.text("PRAGMA table_info(user)")).fetchall()
        cols = [row[1] for row in res]
        if 'role' not in cols:
            db.session.execute(db.text("ALTER TABLE user ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'student'"))
            db.session.commit()
    except Exception as e:
        app.logger.error(f"Failed to ensure role column on user table: {e}")

def ensure_assignment_deadline_columns():
    try:
        tbl = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='assignment'"))
        if not tbl.fetchone():
            return
        res = db.session.execute(db.text("PRAGMA table_info(assignment)"))
        cols = [row[1] for row in res]
        if 'opens_at' not in cols:
            db.session.execute(db.text("ALTER TABLE assignment ADD COLUMN opens_at DATETIME"))
        if 'due_at' not in cols:
            db.session.execute(db.text("ALTER TABLE assignment ADD COLUMN due_at DATETIME"))
        if 'late_policy' not in cols:
            db.session.execute(db.text("ALTER TABLE assignment ADD COLUMN late_policy VARCHAR(20) NOT NULL DEFAULT 'allow'"))
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Failed to ensure assignment deadline columns: {e}")

def ensure_submission_is_late_column():
    try:
        tbl = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='assignment_submission'"))
        if not tbl.fetchone():
            return
        res = db.session.execute(db.text("PRAGMA table_info(assignment_submission)"))
        cols = [row[1] for row in res]
        if 'is_late' not in cols:
            db.session.execute(db.text("ALTER TABLE assignment_submission ADD COLUMN is_late BOOLEAN NOT NULL DEFAULT 0"))
            db.session.commit()
    except Exception as e:
        app.logger.error(f"Failed to ensure is_late column: {e}")


# Ensure tables are created on run
if __name__ == '__main__':
    with app.app_context():
        ensure_user_role_column()
        ensure_assignment_deadline_columns()
        ensure_submission_is_late_column()
        db.create_all()
    app.run(debug=True)

