import os
import re
import json
from typing import List
from google import genai
from pydantic import BaseModel
from datetime import datetime
from fpdf import FPDF
from PyPDF2 import PdfReader
from google.genai import types
import httpx
import pathlib

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

def generate_paper(name_of_the_exam: str, difficulty_level: str, format_of_the_exam: str):
    print("Generating paper for:", name_of_the_exam, "with difficulty level:", difficulty_level, "and format:", format_of_the_exam)
    """
    Generates a paper based on the provided parameters.

    Args:
        name_of_the_exam (str): Name of the exam.
        difficulty_level (str): Difficulty level of the exam.
        format_of_the_exam (str): Format of the exam.

    Returns:
        str: Path to the generated JSON file.
    """
    response = None
    exam_upper = name_of_the_exam.upper()
    if exam_upper == "JEE_MAINS":
        JEE_MAINS_PROMPT = f"""
            You are an expert in creating high-quality exam papers for competitive exams like
                             {exam_upper}
                             Generate a paper with {difficulty_level} difficulty level and format {format_of_the_exam}
                             {jee_mains_context}
            """
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

    # Determine output directory structure to avoid overwrites and to keep papers organized
    base_output_dir = os.path.join("GENERATED_PAPERS", "JSON")
    exam_dir_map = {
        "JEE_MAINS": "MAINS",
        "JEE_ADVANCED": "ADVANCED",
        "NEET_UG": "NEET",
    }
    sub_dir = exam_dir_map.get(exam_upper, "MISC")
    output_dir = os.path.join(base_output_dir, sub_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Build a unique, non-overwriting filename
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_difficulty = str(difficulty_level)
    safe_format = str(format_of_the_exam)
    base_name = f"{exam_upper}_{safe_difficulty}_{safe_format}_{ts}.json"
    filepath = os.path.join(output_dir, base_name)

    # Write generated paper to JSON file
    with open(filepath, 'w', encoding='utf-8') as f:
        text = str(response.text)
        f.write(text)
    return filepath


def offline_scoring(filepath: str, raw_json_paper_path: str):
    # Load the raw JSON paper if provided
    data = None
    if raw_json_paper_path and raw_json_paper_path.endswith(".json") and os.path.exists(raw_json_paper_path):
        with open(raw_json_paper_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

    solution_sheet = json.dumps(data, indent=2) if data is not None else "{}"

    prompt = (
        "I want you to look at actual score sheet and then compare it with the sheet "
        "uploaded by the student and give your response accordingly."
    )

    # Upload user solution file (the path argument naming is a bit confusing; keeping for compatibility)
    user_solution = client.files.upload(file=raw_json_paper_path)

    contents = [prompt, solution_sheet, user_solution]

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[OfflineMCQExamResponse],
        }
    )

    # Save the final result with a unique filename to avoid overwrites
    output_dir = "FINAL_RESULT_OFFLINE"
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"final_result_{ts}.json"
    out_path = os.path.join(output_dir, filename)
    with open(out_path, 'w', encoding='utf-8') as f:
        score_sheet = str(response.text)
        f.write(score_sheet)
    return out_path


