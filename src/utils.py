import os
import re
import json
from typing import List
from fpdf import FPDF
from PyPDF2 import PdfReader

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

def check_online_paper(generated_paper_filepath: str, submitted_answer_sheet_filepath: str, exam_name: str):
    """
    Compares the submitted answers with the generated paper and prints the result for each question.

    Args:
        generated_paper_filepath (str): Path to the generated paper JSON file.
        submitted_answer_sheet_filepath (str): Path to the submitted answer sheet JSON file.

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

    with open(generated_paper_filepath, 'r') as f:
        generated_paper = json.load(f)

    score = 0
    results = []

    # Compare answers for each question
    for question in generated_paper:
        q_num = question.get('question_number')
        correct_answer = question.get('answer')
        submitted_answer = submitted_answers.get(str(q_num)) or submitted_answers.get(q_num)
        is_correct = (str(submitted_answer).strip().lower() == str(correct_answer).strip().lower())
        results.append({
            'question_number': q_num,
            'correct_answer': correct_answer,
            'submitted_answer': submitted_answer,
            'is_correct': is_correct
        })
        if is_correct:
            score += 1

    # Print summary
    print(f"Total Questions: {len(generated_paper)}")
    print(f"Correct Answers: {score}")
    print("Detailed Results:")
    for res in results:
        print(
            f"Q{res['question_number']}: Submitted: {res['submitted_answer']} | Correct: {res['correct_answer']} | {'Correct' if res['is_correct'] else 'Incorrect'}")

    return {
        'score': score,
        'total': len(generated_paper),
        'results': results
    }

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