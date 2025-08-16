import os
from typing import List
from google import genai
from pydantic import BaseModel

model = "gemini-2.5-pro"

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
with open("apikey.txt", 'r') as f:
    api_key = f.read().strip()


# Initialize Gemini client
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
    # Generate paper for JEE Mains
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


    # Create output directory if it doesn't exist
    output_dir = "../GENERATED_PAPERS"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{name_of_the_exam}_{difficulty_level}_{format_of_the_exam}.json"
    filepath = os.path.join(output_dir, filename)

    # Write generated paper to JSON file
    with open(filepath, 'w') as f:
        text = response.text
        f.write(text)
    return filepath
