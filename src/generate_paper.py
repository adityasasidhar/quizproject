import os
import re
import json
from typing import List, Optional
from google import genai
from pydantic import BaseModel
from datetime import datetime
from fpdf import FPDF
from PyPDF2 import PdfReader
from google.genai import types
import httpx
import pathlib
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# --- From school_paper.py ---
class SchoolQuizFormat(BaseModel):
    question_number : str
    question: str
    options: List[str] or None
    answer: str
    solution: str

class SchoolTestFormat(BaseModel):
    question_number : str
    question: str
    answer: str

SUBJECTS = ['BIOLOGY', 'CHEMISTRY', 'ENGLISH', 'MATHEMATICS', 'PHYSICS', 'SOCIAL_SCIENCE']
GRADE = ['9', '10', '11', '12']
BOARD = ['CBSE', 'ICSE', 'STATE','TSBIE']
LANGUAGE = ['ENG', 'HIN', 'TEL']

model = "gemini-2.5-flash-lite"

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
    solution : str

class OfflineMCQExamResponse(BaseModel):
    question_number : str
    marks : int
    reason : str
    solution : str

class OfflineSubjectiveExamResponse(BaseModel):
    question_number : str
    marks : int
    reason : str
    solution : str

jee_mains_context = '''
The JEE Mains paper typically consists of three sections: Physics, Chemistry, and Mathematics. Each section contains multiple-choice questions (MCQs) and numerical value-based questions. The exam is conducted in a computer-based format.
I want you to generate a paper for JEE Mains with the following specifications:\n
I want you to generate a full length jee mains question paper\n
It should have a total of 90 questions, with 30 questions from each subject (Physics, Chemistry, Mathematics). Candidates can attempt a maximum of 75 questions. The questions should be a mix of MCQs and numerical value-based questions.\n
- Total Questions: 90 (30 per subject; candidates can attempt 75)
- Question Types:
- MCQs (with four options, one correct)  
- Numerical value-based questions (no options, answer is a number)
'''

jee_advanced_context = '''
The JEE Advanced paper is designed for admission to the prestigious Indian Institutes of Technology (IITs). It consists of two papers, each with three sections: Physics, Chemistry, and Mathematics. The questions include multiple-choice questions (MCQs), numerical value-based questions, and matching-type questions. The exam is conducted in a computer-based format.
I want you to generate a paper for JEE Advanced with the following specifications:\n
I want you to generate a full length JEE Advanced question paper\n
Each paper should have a total of 54 questions, with 18 questions from each subject (Physics, Chemistry, Mathematics). The questions should be a mix of MCQs, numerical value-based, and matching-type questions.\n
- Total Questions per paper: 54 (18 per subject)
    - Question Types:
        - MCQs (with four options, one or more correct)
        - Numerical value-based questions (no options, answer is a number)
        - Matching-type questions (match the following)
'''
neet_ug_context = '''
The NEET (National Eligibility cum Entrance Test) paper is for admission to medical courses in India. It consists of four sections: Physics, Chemistry, Botany, and Zoology. Each section contains multiple-choice questions (MCQs) with four options and one correct answer. The exam is conducted in a pen-and-paper format.
I want you to generate a paper for NEET with the following specifications:\n
I want you to generate a full length NEET question paper\n
It should have a total of 200 questions, with 50 questions from each subject (Physics, Chemistry, Botany, Zoology). Candidates can attempt a maximum of 180 questions. All questions should be MCQs.\n
- Total Questions: 200 (50 per subject; candidates can attempt 180)
    - Question Types:
        - MCQs (with four options, one correct)
'''

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)
print("API KEY LOADED")


def clean_text(text):
    print("Cleaning Text")
    replacements = {
        '√': 'sqrt', '±': '+/-', '°': ' degrees', '×': 'x', '÷': '/',
        '≠': '!=', '≤': '<=', '≥': '>=', '∞': 'infinity', 'π': 'pi',
        'μ': 'u', 'Δ': 'delta', 'α': 'alpha', 'β': 'beta', 'γ': 'gamma'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text

def load_papers(directory: str) -> List[str]:
    papers = []
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if filename.endswith(".txt"):
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        papers.append(file.read())
                except Exception as e:
                    print(f"Error reading text file {filename}: {e}")
            elif filename.endswith(".pdf"):
                try:
                    reader = PdfReader(file_path)
                    text = ""
                    for page in reader.pages:
                        page_text = page.extract_text() or ""
                        text += page_text
                    papers.append(text)
                except Exception as e:
                    print(f"Error reading PDF {filename}: {e}")
        print(f"Loaded {len(papers)} papers")
        return papers
    except Exception as e:
        print(f"Error loading papers: {e}")
        return []

def generate_paper(name_of_the_exam: str, difficulty_level: Optional[str] = None, format_of_the_exam: Optional[str] = None, subject: Optional[str] = None, grade: Optional[str] = None, board: Optional[str] = None, chapters: Optional[List[str]] = None, language: str = 'ENG'):
    """
    Generates a paper based on the provided parameters.
    """
    print("Generating paper for:", name_of_the_exam)
    response = None
    exam_upper = name_of_the_exam.upper()

    if exam_upper == "JEE_MAINS":
        JEE_MAINS_PROMPT = f'''
            You are an expert in creating high-quality exam papers for competitive exams like
                             {exam_upper}
                             Generate a paper with {difficulty_level} difficulty level and format {format_of_the_exam}
                             {jee_mains_context}
            '''
        response = client.models.generate_content(
            model=model,
            contents=[JEE_MAINS_PROMPT, jee_mains_context],
            config={
                "response_mime_type": "application/json",
                "response_schema": list[PaperFormatForMCQ],
            },
        )
    elif exam_upper == "JEE_ADVANCED":
        response = client.models.generate_content(
            model=model,
            contents="You are an expert in creating high-quality exam papers for competitive exams like "
                     f"{exam_upper}.\n"
                     f"Generate a paper with {difficulty_level} difficulty level and format {format_of_the_exam}.\n"
                     f"{jee_advanced_context}",
            config={
                "response_mime_type": "application/json",
                "response_schema": list[PaperFormatForMCQ],
            },
        )
    elif exam_upper == "NEET_UG":
        response = client.models.generate_content(
            model=model,
            contents="You are an expert in creating high-quality exam papers for competitive exams like "
                     f"{exam_upper}.\n"
                     f"Generate a paper with {difficulty_level} difficulty level and format {format_of_the_exam}.\n"
                     f"{neet_ug_context}",
            config={
                "response_mime_type": "application/json",
                "response_schema": list[PaperFormatForMCQ],
            },
        )
    elif exam_upper == "SCHOOL_QUIZ":
        prompt = '''
        You are an intelligent AI whose main job is to generate test for school students,
        you will be given their !textbook chapter or the textbook itself so
        you can take that as context and generate questions based on them,
        mind the grade of the student too, make sure the questions are of good quality and adhere to safety
        standards, make sure you reply in the proper format.
        Give your questions based on the activity sections of the chapter
        generate about 20 questions.'''

        if subject.upper() in SUBJECTS and grade in GRADE and board.upper() in BOARD and language.upper() in LANGUAGE:
            content = [prompt,
                       f"You are generating a school quiz for {subject.upper()} grade {grade} board {board.upper()}"]
            base_dir = os.path.dirname(os.path.abspath(__file__))
            context_dir = os.path.join(base_dir, "..", "CONTEXT", "BOOKS", board, grade, language, subject)
            for chapter in chapters:
                pdf_path = os.path.join(context_dir, chapter)
                print(f"Resolved PDF path: {pdf_path}")
                if os.path.exists(pdf_path):
                    chapter_file = pathlib.Path(pdf_path)
                    uploaded_file = client.files.upload(file=chapter_file)
                    content.append(uploaded_file)
                else:
                    print(f"File not found: {pdf_path}")
            response = client.models.generate_content(
                    model=model,
                    contents= content,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": list[SchoolQuizFormat],
                    },
                )
    elif exam_upper == "SCHOOL_TEST":
        prompt = '''
        You are an intelligent AI whose main job is to generate test for school students,
        you will be given their !textbook chapter or the textbook itself so
        you can take that as context and generate questions based on them,
        mind the grade of the student too, make sure the questions a
        re of good quality and adhere to safety
        standards, make sure you reply in the proper format.
        Give your questions based on the exercise sections of the chapter
        generate about 10 questions.'''

        if subject.upper() in SUBJECTS and grade in GRADE and board.upper() in BOARD and language.upper() in LANGUAGE:
            content = [prompt,
                       f"You are generating a school test for {subject.upper()} grade {grade} board {board.upper()}"]
            base_dir = os.path.dirname(os.path.abspath(__file__))
            context_dir = os.path.join(base_dir, "..", "CONTEXT", "BOOKS", board, grade, language, subject)
            for chapter in chapters:
                pdf_path = os.path.join(context_dir, chapter)
                print(f"Resolved PDF path: {pdf_path}")
                if os.path.exists(pdf_path):
                    chapter_file = pathlib.Path(pdf_path)
                    uploaded_file = client.files.upload(file=chapter_file)
                    content.append(uploaded_file)
                else:
                    print(f"File not found: {pdf_path}")
            response = client.models.generate_content(
                    model=model,
                    contents= content,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": list[SchoolTestFormat],
                    },
                )

    if response is None:
        print(f"Could not generate paper for exam type: {name_of_the_exam}. Check parameters.")
        return None

    # Determine output directory structure
    base_output_dir = os.path.join("GENERATED_PAPERS", "JSON")
    exam_dir_map = {
        "JEE_MAINS": "MAINS",
        "JEE_ADVANCED": "ADVANCED",
        "NEET_UG": "NEET",
        "SCHOOL_QUIZ": os.path.join("SCHOOL", "QUIZ"),
        "SCHOOL_TEST": os.path.join("SCHOOL", "TEST"),
    }
    sub_dir = exam_dir_map.get(exam_upper, "MISC")
    output_dir = os.path.join(base_output_dir, sub_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Build a unique filename
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if exam_upper in ["SCHOOL_QUIZ", "SCHOOL_TEST"]:
        base_name = f"{exam_upper}_{subject}_{grade}_{board}_{ts}.json"
    else:
        safe_difficulty = str(difficulty_level)
        safe_format = str(format_of_the_exam)
        base_name = f"{exam_upper}_{safe_difficulty}_{safe_format}_{ts}.json"
    
    filepath = os.path.join(output_dir, base_name)

    # Write generated paper to JSON file
    with open(filepath, 'w', encoding='utf-8') as f:
        text = str(response.text)
        f.write(text)
    return filepath


def offline_scoring(actual_solution: str, users_solution: str):
    prompt = (
        "I want you to look at actual score sheet and then compare it with the sheet "
        "uploaded by the student and give your response accordingly."
    )
    user_solution = client.files.upload(file=users_solution)
    actual_solution = client.files.upload(file=actual_solution)

    contents = [prompt, actual_solution, user_solution]

    response = client.models.generate_content(
        model= "gemini-2.5-flash-lite",
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[OfflineMCQExamResponse],
        }
    )
    output_dir = "FINAL_RESULT_OFFLINE"
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"final_result_{ts}.json"
    out_path = os.path.join(output_dir, filename)
    with open(out_path, 'w', encoding='utf-8') as f:
        score_sheet = str(response.text)
        f.write(score_sheet)
    return out_path
