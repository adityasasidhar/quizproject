from fpdf import FPDF
import json
import re

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

    # Generate Answer Sheet PDF
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


extract_and_convert("../GENERATED_PAPERS/generated_paper.json")