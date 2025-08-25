import os
import json
import base64
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
from src.generate_paper import generate_paper
from google import genai
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

with open("apikey.txt", 'r') as f:
    api_key = f.read().strip()

# Initialize Gemini client
client = genai.Client(api_key=api_key)

# Allowed file extensions for answer uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Home page with options for online and offline exams"""
    return render_template('index.html')

@app.route('/exam_setup', methods=['GET', 'POST'])
def exam_setup():
    if request.method == 'POST':
        exam_mode = request.form.get('exam_mode')
        exam_name = request.form.get('exam_name')
        difficulty = request.form.get('difficulty')
        exam_format = request.form.get('exam_format')

        json_path = generate_paper(exam_name, difficulty, exam_format)
        session['json_path'] = json_path
        session['exam_name'] = exam_name
        session['difficulty'] = difficulty
        session['exam_format'] = exam_format
        
        if exam_mode == 'online':
            return redirect(url_for('online_exam'))
        else:  # offline
            return redirect(url_for('offline_exam'))
    
    return render_template('exam_setup.html')

@app.route('/online_exam')
def online_exam():
    """Display online exam with questions and options"""
    json_path = session.get('json_path')
    
    if not json_path or not os.path.exists(json_path):
        return redirect(url_for('exam_setup'))
    
    with open(json_path, 'r') as f:
        questions = json.load(f)
    
    return render_template('online_exam.html', questions=questions)

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    """Handle exam submission and calculate score"""
    json_path = session.get('json_path')
    
    if not json_path or not os.path.exists(json_path):
        return redirect(url_for('exam_setup'))
    
    with open(json_path, 'r') as f:
        questions = json.load(f)
    
    # Get user answers from form
    user_answers = {}
    for q in questions:
        q_id = str(q['question_number'])
        user_answers[q_id] = request.form.get(q_id, '')
    
    # Calculate score
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
def offline_exam():
    """Generate and provide downloadable exam paper"""
    json_path = session.get('json_path')
    
    if not json_path or not os.path.exists(json_path):
        return redirect(url_for('exam_setup'))
    
    with open(json_path, 'r') as f:
        questions = json.load(f)
    
    return render_template('offline_exam.html', 
                          questions=questions, 
                          json_path=json_path)

@app.route('/download_exam')
def download_exam():
    """Download the generated exam paper as JSON"""
    json_path = session.get('json_path')
    
    if not json_path or not os.path.exists(json_path):
        return redirect(url_for('exam_setup'))
    
    return send_file(json_path, as_attachment=True)

@app.route('/upload_answers', methods=['GET', 'POST'])
def upload_answers():
    """Handle upload of answer images and process them"""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'answer_file' not in request.files:
            return render_template('upload_answers.html', error="No file part")
        
        file = request.files['answer_file']
        
        # If user does not select file, browser also submits an empty part without filename
        if file.filename == '':
            return render_template('upload_answers.html', error="No selected file")
        
        if file and allowed_file(file.filename):
            # Save the file temporarily
            temp_dir = tempfile.mkdtemp()
            filename = secure_filename(file.filename)
            filepath = os.path.join(temp_dir, filename)
            file.save(filepath)
            
            # Process the image with Gemini
            try:
                json_path = session.get('json_path')
                with open(json_path, 'r') as f:
                    questions = json.load(f)
                
                # Convert image to base64 for Gemini
                with open(filepath, "rb") as img_file:
                    image_bytes = img_file.read()
                
                image_parts = [
                    {
                        "mime_type": f"image/{filepath.split('.')[-1]}",
                        "data": base64.b64encode(image_bytes).decode('utf-8')
                    }
                ]
                
                # Create prompt for Gemini
                prompt = f"""
                I have an exam with the following questions:
                
                {json.dumps([{'question_number': q['question_number'], 'question': q['question'], 'answer': q['answer']} for q in questions], indent=2)}
                
                The image contains handwritten or typed answers to these questions. 
                Extract the answers from the image and match them to the questions.
                
                Return a JSON array with the following structure:
                [
                  {{
                    "question_number": 1,
                    "extracted_answer": "the answer extracted from the image",
                    "correct_answer": "the correct answer from the question data",
                    "is_correct": true/false
                  }},
                  ...
                ]
                
                If you can't find an answer for a question, use an empty string for "extracted_answer" and set "is_correct" to false.
                """
                
                # Call Gemini to analyze the image
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=f"{prompt}",
                )

                try:
                    # Extract JSON from the response
                    response_text = response.text
                    if "```json" in response_text:
                        json_content = response_text.split("```json")[1].split("```")[0].strip()
                    else:
                        json_content = response_text
                    
                    results = json.loads(json_content)
                    
                    # Calculate score
                    score = sum(1 for r in results if r.get('is_correct', False))
                    total = len(results)
                    percentage = (score / total) * 100 if total > 0 else 0
                    
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
    app.run(debug=True)