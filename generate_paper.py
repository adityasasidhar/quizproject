import os
import time
from typing import List
from google import genai
from pydantic import BaseModel

from fpdf import FPDF
import json
import re

# Model name for Gemini API
model = "gemini-2.5-pro"

# Context string for JEE Mains paper generation
jee_mains_context = """
The JEE Mains paper typically consists of three sections: Physics, Chemistry, and Mathematics. Each section contains multiple-choice questions (MCQs) and numerical value-based questions. The exam is conducted in a computer-based format.
I want you to generate a paper for JEE Mains with the following specifications:\n
I want you to generate a full length jee mains question paper\n
It should have a total of 90 questions, with 30 questions from each subject (Physics, Chemistry, Mathematics). Candidates can attempt a maximum of 75 questions. The questions should be a mix of MCQs and numerical value-based questions.\n
- Total Questions: 90 (30 per subject; candidates can attempt 75)
- Question Types:
- MCQs (with four options, one correct)  
- Numerical value-based questions (no options, answer is a number)
"""

# Context string for JEE Advanced paper generation
jee_advanced_context = """
The JEE Advanced paper is designed for admission to the prestigious Indian Institutes of Technology (IITs). It consists of two papers, each with three sections: Physics, Chemistry, and Mathematics. The questions include multiple-choice questions (MCQs), numerical value-based questions, and matching-type questions. The exam is conducted in a computer-based format.
I want you to generate a paper for JEE Advanced with the following specifications:\n
I want you to generate a full length JEE Advanced question paper\n
Each paper should have a total of 54 questions, with 18 questions from each subject (Physics, Chemistry, Mathematics). The questions should be a mix of MCQs, numerical value-based, and matching-type questions.\n
- Total Questions per paper: 54 (18 per subject)
    - Question Types:
        - MCQs (with four options, one or more correct)
        - Numerical value-based questions (no options, answer is a number)
        - Matching-type questions (match the following)
"""

# Context string for NEET UG paper generation
neet_ug_context = """
The NEET (National Eligibility cum Entrance Test) paper is for admission to medical courses in India. It consists of four sections: Physics, Chemistry, Botany, and Zoology. Each section contains multiple-choice questions (MCQs) with four options and one correct answer. The exam is conducted in a pen-and-paper format.
I want you to generate a paper for NEET with the following specifications:\n
I want you to generate a full length NEET question paper\n
It should have a total of 200 questions, with 50 questions from each subject (Physics, Chemistry, Botany, Zoology). Candidates can attempt a maximum of 180 questions. All questions should be MCQs.\n
- Total Questions: 200 (50 per subject; candidates can attempt 180)
    - Question Types:
        - MCQs (with four options, one correct)
"""

# Pydantic model for MCQ format questions
class PaperFormatForMCQ(BaseModel):
    question_number: int
    question: str
    options: List[str]
    answer: str

# Pydantic model for subjective format questions
class PaperFormatForSubjective(BaseModel):
    question_number: int
    question: str
    answer: str

# Read API key from file
with open("apikey.txt",'r') as f:
    api_key = f.read().strip()

# Initialize Gemini client
client = genai.Client(api_key=api_key)

def generate_paper(name_of_the_exam: str, difficulty_level: str, format_of_the_exam: str):
    """
    Generates a paper based on the provided parameters.

    Args:
        name_of_the_exam (str): Name of the exam.
        difficulty_level (str): Difficulty level of the exam.
        format_of_the_exam (str): Format of the exam.

    Returns:
        str: Path to the generated PDF file.
    """
    response = None
    # Generate paper for JEE Mains
    if name_of_the_exam.upper() == "JEE_MAINS":
        response = client.models.generate_content(
            model= model,
            contents="You are an expert in creating high-quality exam papers for competitive exams like "
                     f"{name_of_the_exam.upper()}.\n"
                     f"Generate a paper with {difficulty_level} difficulty level and format {format_of_the_exam}.\n"
                     f"{jee_mains_context}",
            config={
                "response_mime_type": "application/json",
                "response_schema": list[PaperFormatForMCQ],
            },
        )
    # Generate paper for JEE Advanced
    elif name_of_the_exam.upper() == "JEE_ADVANCED":
        response = client.models.generate_content(
            model= model,
            contents="You are an expert in creating high-quality exam papers for competitive exams like "
                     f"{name_of_the_exam.upper()}.\n"
                     f"Generate a paper with {difficulty_level} difficulty level and format {format_of_the_exam}.\n"
                     f"{jee_advanced_context}",
            config={
                "response_mime_type": "application/json",
                "response_schema": list[PaperFormatForMCQ],
            },
        )
    # Generate paper for NEET UG
    elif name_of_the_exam.upper() == "NEET_UG":
        response = client.models.generate_content(
            model= model,
            contents="You are an expert in creating high-quality exam papers for competitive exams like "
                     f"{name_of_the_exam.upper()}.\n"
                     f"Generate a paper with {difficulty_level} difficulty level and format {format_of_the_exam}.\n"
                     f"{neet_ug_context}",
            config={
                "response_mime_type": "application/json",
                "response_schema": list[PaperFormatForMCQ],
            },
        )

    def clean_text(text):
        """
        Cleans and replaces special characters in the text for better readability.

        Args:
            text (str): Input text.

        Returns:
            str: Cleaned text.
        """
        replacements = {
            '√': 'sqrt', '±': '+/-', '°': ' degrees', '×': 'x', '÷': '/',
            '≠': '!=', '≤': '<=', '≥': '>=', '∞': 'infinity', 'π': 'pi',
            'μ': 'u', 'Δ': 'delta', 'α': 'alpha', 'β': 'beta', 'γ': 'gamma'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Remove non-ASCII characters
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        return text

    def extract_and_convert(filepath):
        """
        Extracts questions and answers from the JSON file and generates PDFs for the question paper and answer sheet.

        Args:
            filepath (str): Path to the JSON file.

        Returns:
            tuple: Paths to the generated question paper and answer sheet PDFs.
        """
        if not filepath.endswith(".json"):
            return None, None

        # Load questions from JSON file
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Group questions by subject if available
        subjects = {}
        for item in data:
            subject = item.get('subject', 'General')
            subjects.setdefault(subject, []).append(item)

        # Generate Question Paper PDF
        question_pdf = FPDF()
        question_pdf.add_page()
        question_pdf.set_font("Arial", 'B', 16)
        question_pdf.cell(0, 12, txt="Question Paper", ln=True, align='C')
        question_pdf.ln(8)

        # Add questions to PDF, grouped by subject
        for subject, questions in subjects.items():
            question_pdf.set_font("Arial", 'B', 14)
            question_pdf.cell(0, 10, txt=f"{subject} Section", ln=True)
            question_pdf.set_font("Arial", size=12)
            question_pdf.ln(2)
            for item in questions:
                question_text = clean_text(item['question'])
                question_pdf.multi_cell(0, 10, f"Q{item['question_number']}: {question_text}")
                if 'options' in item and item['options']:
                    for idx, opt in enumerate(item['options']):
                        option_text = clean_text(opt)
                        question_pdf.multi_cell(0, 8, f"    {chr(65 + idx)}. {option_text}")
                question_pdf.ln(4)
            question_pdf.ln(6)

        question_pdf_path = filepath.replace(".json", "_questions.pdf")
        question_pdf.output(question_pdf_path)

        # Generate Answer Sheet PDF
        answer_pdf = FPDF()
        answer_pdf.add_page()
        answer_pdf.set_font("Arial", 'B', 16)
        answer_pdf.cell(0, 12, txt="Answer Sheet", ln=True, align='C')
        answer_pdf.ln(8)

        # Add answers to PDF, grouped by subject
        for subject, questions in subjects.items():
            answer_pdf.set_font("Arial", 'B', 14)
            answer_pdf.cell(0, 10, txt=f"{subject} Section", ln=True)
            answer_pdf.set_font("Arial", size=12)
            answer_pdf.ln(2)
            for item in questions:
                answer_text = clean_text(str(item['answer']))
                answer_pdf.cell(0, 10, f"Q{item['question_number']}: {answer_text}", ln=True)
            answer_pdf.ln(6)

        answer_pdf_path = filepath.replace(".json", "_answers.pdf")
        answer_pdf.output(answer_pdf_path)

        return question_pdf_path, answer_pdf_path


    # Create output directory if it doesn't exist
    output_dir = "GENERATED_PAPERS"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{name_of_the_exam}_{difficulty_level}_{format_of_the_exam}.json"
    filepath = os.path.join(output_dir, filename)

    # Write generated paper to JSON file
    with open(filepath, 'w') as f:
        text = response.text
        f.write(text)
    return filepath

def check_online_paper(generated_paper_filepath: str, submitted_answer_sheet_filepath: str, exam_name: str):
    """
    Compares the submitted answers with the generated paper and prints the result for each question.
    Handles different exam schemas and scoring for NEET, JEE Mains, and JEE Advanced.

    Args:
        generated_paper_filepath (str): Path to the generated paper JSON file.
        submitted_answer_sheet_filepath (str): Path to the submitted answer sheet JSON file.
        exam_name (str): Name of the exam ("NEET_UG", "JEE_MAINS", "JEE_ADVANCED").

    Returns:
        dict: Dictionary containing score and detailed results.

    Expected format for submitted_answer_sheet_filepath (JSON):
        {
            "1": "A",
            "2": "B",
            "3": "42",
            ...
        }
    Keys can be either strings or integers representing question_number.
    Values are the submitted answers (option letter or numerical value).
    """
    # Check if generated paper file exists
    if not os.path.exists(generated_paper_filepath):
        print(f"File {generated_paper_filepath} does not exist.")
        return None

    # Check if file is a JSON file
    if not generated_paper_filepath.endswith(".json"):
        print("Generated paper file is not a JSON file.")
        return None

    # Load submitted answers
    with open(submitted_answer_sheet_filepath, 'r') as f:
        submitted_answers = json.load(f)

    # Load generated paper
    with open(generated_paper_filepath, 'r') as f:
        generated_paper = json.load(f)

    # Set scoring rules based on exam
    exam_name = exam_name.upper()
    if exam_name == "NEET_UG":
        # NEET: +4 for correct, -1 for incorrect, 0 for not attempted
        marks_correct = 4
        marks_incorrect = -1
        marks_unattempted = 0
    elif exam_name == "JEE_MAINS":
        # JEE Mains: +4 for correct, -1 for incorrect (MCQ), 0 for not attempted/numerical
        marks_correct = 4
        marks_incorrect = -1
        marks_unattempted = 0
    elif exam_name == "JEE_ADVANCED":
        # JEE Advanced: scoring varies, but for simplicity:
        # MCQ (single correct): +3, -1; MCQ (multiple correct): +4, -2; Numerical: +3, 0; Matching: +4, 0
        # We'll infer type from question if possible, else default to +3/-1
        pass  # Will handle per question below
    else:
        print("Unknown exam name. Defaulting to +1 for correct, 0 for incorrect.")
        marks_correct = 1
        marks_incorrect = 0
        marks_unattempted = 0

    total_score = 0
    results = []

    for question in generated_paper:
        q_num = question.get('question_number')
        correct_answer = question.get('answer')
        submitted_answer = submitted_answers.get(str(q_num)) or submitted_answers.get(q_num)
        question_type = None

        # Try to infer question type for JEE Advanced
        if exam_name == "JEE_ADVANCED":
            if 'options' in question and isinstance(question['options'], list):
                if isinstance(correct_answer, list) and len(correct_answer) > 1:
                    question_type = "MCQ_MULTIPLE"
                    marks_correct = 4
                    marks_incorrect = -2
                else:
                    question_type = "MCQ_SINGLE"
                    marks_correct = 3
                    marks_incorrect = -1
            elif 'match' in question or 'matching' in question.get('question', '').lower():
                question_type = "MATCHING"
                marks_correct = 4
                marks_incorrect = 0
            else:
                question_type = "NUMERICAL"
                marks_correct = 3
                marks_incorrect = 0

        # Determine correctness
        if submitted_answer is None or str(submitted_answer).strip() == "":
            is_correct = False
            attempted = False
        else:
            attempted = True
            # For MCQ multiple correct, compare as set
            if exam_name == "JEE_ADVANCED" and question_type == "MCQ_MULTIPLE":
                if isinstance(correct_answer, list):
                    submitted_set = set(str(submitted_answer).replace(" ", "").upper())
                    correct_set = set("".join([str(x).upper() for x in correct_answer]))
                    is_correct = submitted_set == correct_set
                else:
                    is_correct = str(submitted_answer).strip().lower() == str(correct_answer).strip().lower()
            else:
                is_correct = str(submitted_answer).strip().lower() == str(correct_answer).strip().lower()

        # Score calculation
        if attempted:
            if is_correct:
                score = marks_correct
            else:
                score = marks_incorrect
        else:
            score = marks_unattempted

        total_score += score
        results.append({
            'question_number': q_num,
            'correct_answer': correct_answer,
            'submitted_answer': submitted_answer,
            'is_correct': is_correct,
            'score': score
        })

    # Print summary
    print(f"Total Questions: {len(generated_paper)}")
    print(f"Total Score: {total_score}")
    print("Detailed Results:")
    for res in results:
        print(f"Q{res['question_number']}: Submitted: {res['submitted_answer']} | Correct: {res['correct_answer']} | {'Correct' if res['is_correct'] else 'Incorrect'} | Score: {res['score']}")

    return {
        'score': total_score,
        'total_questions': len(generated_paper),
        'results': results
    }
