import os
import json
import base64
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from src.generate_paper import generate_paper
from src.utils import *
from google import genai
import tempfile
from werkzeug.utils import secure_filename
from functools import wraps
from dotenv import load_dotenv

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            error = 'Invalid username or password.'
    return render_template('login.html', error=error)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            error = 'All fields are required.'
        elif User.query.filter_by(username=username).first():
            error = 'Username already exists.'
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
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
    """Handle exam submission and calculate score"""
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
