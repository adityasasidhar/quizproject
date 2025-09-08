import os
import re
import io
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
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

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

model = "gemini-2.5-flash-lite"

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)
print("API KEY LOADED")

SUBJECTS = ['BIOLOGY', 'CHEMISTRY', 'ENGLISH', 'MATHEMATICS', 'PHYSICS', 'SOCIAL_SCIENCE']
GRADE = ['9', '10', '11', '12']
BOARD = ['CBSE', 'ICSE', 'STATE','TSBIE']
LANGUAGE = ['ENG', 'HIN', 'TEL']

Bio_9th_english_chapters = [
    "AnimalTissue.pdf",
    "CellitsstructureandFunctions.pdf",
    "PlantTissue.pdf"
]
Phy_9th_english_chapters = [
    "Motion.pdf",
    "Matteraroundus.pdf"
]
def generate_school_quiz(subject: str, grade: str, board: str, chapters: List[str], language: str = 'ENG'):
    prompt = """
    You are an intelligent AI whose main job is to generate test for school students,
    you will be given their !textbook chapter or the textbook itself so
    you can take that as context and generate questions based on them,
    mind the grade of the student too, make sure the questions are of good quality and adhere to safety
    standards, make sure you reply in the proper format.
    Give your questions based on the activity sections of the chapter
    generate about 20 questions."""

    if subject.upper() in SUBJECTS and grade.upper() in GRADE and board.upper() in BOARD and language.upper() in LANGUAGE:
        content = [prompt,
                   f"You are generating a school quiz for {subject.upper()} grade {grade.upper()} board {board.upper()}"]
        base_dir = os.path.dirname(os.path.abspath(__file__))
        context_dir = os.path.join(base_dir, "..", "CONTEXT", "BOOKS", board, grade, language, subject)
        uploaded_files = []
        for chapter in chapters:
            pdf_path = os.path.join(context_dir, chapter)
            print(f"Resolved PDF path: {pdf_path}")
            if os.path.exists(pdf_path):
                chapter_file = pathlib.Path(pdf_path)
                uploaded_file = client.files.upload(file=chapter_file)
                content = content + [uploaded_file]
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
        response_text = response.text
        base_output_dir = os.path.join("GENERATED_PAPERS", "JSON")
        exam_dir_map = {
            ""
        }

def generate_school_test(subject: str, grade: str, board: str, chapters: List[str], language: str = 'ENG'):
    prompt = """
    You are an intelligent AI whose main job is to generate test for school students,
    you will be given their !textbook chapter or the textbook itself so
    you can take that as context and generate questions based on them,
    mind the grade of the student too, make sure the questions a
    re of good quality and adhere to safety
    standards, make sure you reply in the proper format.
    Give your questions based on the exercise sections of the chapter
    generate about 10 questions."""

    if subject.upper() in SUBJECTS and grade.upper() in GRADE and board.upper() in BOARD and language.upper() in LANGUAGE:
        content = [prompt,
                   f"You are generating a school test for {subject.upper()} grade {grade.upper()} board {board.upper()}"]
        base_dir = os.path.dirname(os.path.abspath(__file__))
        context_dir = os.path.join(base_dir, "..", "CONTEXT", "BOOKS", board, grade, language, subject)
        uploaded_files = []
        for chapter in chapters:
            pdf_path = os.path.join(context_dir, chapter)
            print(f"Resolved PDF path: {pdf_path}")
            if os.path.exists(pdf_path):
                chapter_file = pathlib.Path(pdf_path)
                uploaded_file = client.files.upload(file=chapter_file)
                content = content + [uploaded_file]
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
        return response.text