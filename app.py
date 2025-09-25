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

load_dotenv() # Load environment variables from .env file

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

api_key = os.getenv("GEMINI_API_KEY")

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

@app.route('/exam_selection')
@login_required
def exam_selection():
    exam_type = request.args.get('exam_type')
    if not exam_type:
        return redirect(url_for('index'))
    return render_template('exam_selection.html', exam_type=exam_type)

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
        chapters_str = request.form.get('chapters')
        chapters = [c.strip() for c in chapters_str.split(',')] if chapters_str else []

        json_path = generate_paper(
            name_of_the_exam=school_exam_type,
            subject=subject,
            grade=grade,
            board=board,
            chapters=chapters
        )
        session['exam_name'] = school_exam_type
        session['subject'] = subject
        session['grade'] = grade
        session['board'] = board
        session['chapters'] = chapters
    else:
        difficulty = request.form.get('difficulty')
        exam_format = request.form.get('exam_format')

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
            details = {'results': results}
            existing = AssignmentSubmission.query.filter_by(assignment_id=assignment_id, user_id=user.id).first()
            if existing:
                existing.score = score
                existing.total = total
                existing.percentage = percentage
                existing.details_json = json.dumps(details)
                existing.submitted_at = datetime.utcnow()
            else:
                sub = AssignmentSubmission(
                    assignment_id=assignment_id,
                    user_id=user.id,
                    score=score,
                    total=total,
                    percentage=percentage,
                    details_json=json.dumps(details)
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
    """Handle upload of answer images and process them"""
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
                
                with open(filepath, "rb") as img_file:
                    image_bytes = img_file.read()
                
                image_parts = [
                    {
                        "mime_type": f"image/{filepath.split('.')[-1]}",
                        "data": base64.b64encode(image_bytes).decode('utf-8')
                    }
                ]
                
                prompt = f"""
                I have an exam with the following questions:
                {json.dumps([{'question_number': q['question_number'], 'question': q['question'], 'answer': q['answer']} for q in questions], indent=2)}
                The image contains handwritten or typed answers to these questions. 
                Extract the answers from the image and match them to the questions.
                Return a JSON array with the structure:
                [ {{"question_number": 1, "extracted_answer": "...", "correct_answer": "...", "is_correct": true/false}} ]
                If you can't find an answer, use an empty string for "extracted_answer" and set "is_correct" to false.
                """
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=[prompt, image_parts[0]],
                )

                try:
                    response_text = response.text
                    if "```json" in response_text:
                        json_content = response_text.split("```json")[1].split("```")[0].strip()
                    else:
                        json_content = response_text
                    
                    results = json.loads(json_content)
                    
                    score = sum(1 for r in results if r.get('is_correct', False))
                    total = len(results)
                    percentage = (score / total) * 100 if total > 0 else 0

                    # Set session flag after successful upload
                    session['answers_uploaded'] = True
                    
                    return render_template('results.html', 
                                          results=results, 
                                          score=score, 
                                          total=total, 
                                          percentage=percentage,
                                          is_uploaded=True)
                except Exception as e:
                    return render_template('upload_answers.html', 
                                          error=f"Error parsing Gemini response: {str(e)}",
                                          response_text=response.text)
            
            except Exception as e:
                return render_template('upload_answers.html', error=f"Error processing image: {str(e)}")
            
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
        
        else:
            return render_template('upload_answers.html', 
                                  error="File type not allowed. Please upload a JPG, JPEG, or PNG image.")
    
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


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    json_path = db.Column(db.String(255), nullable=False)
    config_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    details_json = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('assignment_id', 'user_id', name='uq_assignment_user'),)


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
    posts = ClassPost.query.filter_by(classroom_id=classroom.id).order_by(ClassPost.created_at.desc()).all()
    assignments = Assignment.query.filter_by(classroom_id=classroom.id).order_by(Assignment.created_at.desc()).all()
    is_teacher = membership.role == 'teacher'
    return render_template('classroom.html', classroom=classroom, posts=posts, assignments=assignments, is_teacher=is_teacher)


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
    assignment = Assignment(classroom_id=class_id, title=title, description=description, json_path=json_path, config_json=json.dumps(config))
    db.session.add(assignment)
    db.session.commit()
    flash('Assignment created successfully.', 'success')
    return redirect(url_for('classroom_view', class_id=class_id))


@app.route('/classroom/<int:class_id>/assignments/<int:assignment_id>/start')
@login_required
def start_assignment(class_id, assignment_id):
    classroom, membership, redirect_resp = require_membership(class_id)
    if redirect_resp:
        return redirect_resp
    assignment = Assignment.query.filter_by(id=assignment_id, classroom_id=class_id).first_or_404()
    session['json_path'] = assignment.json_path
    session['assignment_id'] = assignment.id
    session['answers_uploaded'] = False
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


# Ensure tables are created on run
if __name__ == '__main__':
    with app.app_context():
        ensure_user_role_column()
        db.create_all()
    app.run(debug=True)


