import os
import json
import re

from certifi import contents
from fpdf import FPDF
from typing import List
from google import genai
from pydantic import BaseModel
from datetime import datetime

model = "gemini-2.5-pro"

def clean_text(text):
    replacements = {
        '√': 'sqrt', '±': '+/-', '°': ' degrees', '×': 'x', '÷': '/',
        '≠': '!=', '≤': '<=', '≥': '>=', '∞': 'infinity', 'π': 'pi',
        'μ': 'u', 'Δ': 'delta', 'α': 'alpha', 'β': 'beta', 'γ': 'gamma'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text

def extract_and_convert(filepath):
    if not filepath.endswith(".json"):
        return None, None

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
                    question_pdf.multi_cell(0, 8, f"    {chr(65+idx)}. {option_text}")
            question_pdf.ln(4)
        question_pdf.ln(6)

    question_pdf_path = filepath.replace(".json", "_questions.pdf")
    question_pdf.output(question_pdf_path)
    answer_pdf = FPDF()
    answer_pdf.add_page()
    answer_pdf.set_font("Arial", 'B', 16)
    answer_pdf.cell(0, 12, txt="Answer Sheet", ln=True, align='C')
    answer_pdf.ln(8)

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

class PaperFormatForMCQ(BaseModel):
    question_number: int
    question: str
    options: List[str]
    answer: str
    solution : str

class PaperFormatForSubjective(BaseModel):
    question_number: int
    question: str
    answer: str

class OfflineMCQExamResponse(BaseModel):
    question_number : str
    marks : int
    reason : str

class OfflineSubjectiveExamResponse(BaseModel):
    question_number : str
    marks : int
    reason : str

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
neet_ug_context = """
The NEET (National Eligibility cum Entrance Test) paper is for admission to medical courses in India. It consists of four sections: Physics, Chemistry, Botany, and Zoology. Each section contains multiple-choice questions (MCQs) with four options and one correct answer. The exam is conducted in a pen-and-paper format.
I want you to generate a paper for NEET with the following specifications:\n
I want you to generate a full length NEET question paper\n
It should have a total of 200 questions, with 50 questions from each subject (Physics, Chemistry, Botany, Zoology). Candidates can attempt a maximum of 180 questions. All questions should be MCQs.\n
- Total Questions: 200 (50 per subject; candidates can attempt 180)
    - Question Types:
        - MCQs (with four options, one correct)
"""

with open("apikey.txt", 'r') as f:
    api_key = f.read().strip()

client = genai.Client(api_key=api_key)

def generate_paper(name_of_the_exam: str, difficulty_level: str, format_of_the_exam: str):
    print("Generating paper for:", name_of_the_exam, "with difficulty level:", difficulty_level, "and format:", format_of_the_exam)
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
    if name_of_the_exam.upper() == "JEE_MAINS":
        response = client.models.generate_content(
            model=model,
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
            model=model,
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
            model=model,
            contents="You are an expert in creating high-quality exam papers for competitive exams like "
                     f"{name_of_the_exam.upper()}.\n"
                     f"Generate a paper with {difficulty_level} difficulty level and format {format_of_the_exam}.\n"
                     f"{neet_ug_context}",
            config={
                "response_mime_type": "application/json",
                "response_schema": list[PaperFormatForMCQ],
            },
        )

    output_dir = "../GENERATED_PAPERS"

    os.makedirs(output_dir, exist_ok=True)
    filename = f"{name_of_the_exam}_{difficulty_level}_{format_of_the_exam}.json"
    filepath = os.path.join(output_dir, filename)

    # Write generated paper to JSON file
    with open(filepath, 'w') as f:
        text = response.text
        f.write(text)
    return filepath


def offline_scoring(filepath : str, raw_json_paper_path : str):
    if filepath.endswith(".json"):
        with open('raw_json_paper_path', 'r') as f:
            data = json.load(f)

    solution_sheet = json.dumps(data, indent=2)

    prompt = "I want you to look at actuall score sheet and then compare it with the sheet uploaded by the student and give your response accordingly."

    user_solution = client.files.upload(file = raw_json_paper_path)

    contents = [prompt, solution_sheet, user_solution]

    response = client.models.generate_content(
        model = model,
        contents = contents,
        config = {
            "response_mime_type": "application/json",
            "response_schema": list[OfflineMCQExamResponse],
        }
    )
    output_dir = "../FINAL_RESULT_OFFLINE"

    os.makedirs(output_dir, exist_ok=True)
    filename = f"final_result.json"
    filepath = os.path.join(output_dir, filename)
    with open('final_result.json', 'w') as f:
        score_sheet = response.text
        f.write(score_sheet)
    return filepath


