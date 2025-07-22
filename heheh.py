import os
import json
import time
from google import genai
from pydantic import BaseModel

# --- PDF Generation Imports ---
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


# --- Pydantic Model for a single Question-Answer pair ---
# Corrected the model to represent one question and its answer.
class QuestionAnswer(BaseModel):
    """Defines the structure for a single question and its corresponding answer."""
    question: str
    options: dict  # e.g., {"A": "Option 1", "B": "Option 2", ...}
    answer: str  # e.g., "A"


# --- PDF Creation Function ---
def create_pdf(paper_data: list[QuestionAnswer], exam_name: str, difficulty: str, file_name: str):
    """
    Creates a formatted PDF document from the generated exam paper data.

    Args:
        paper_data (list[QuestionAnswer]): The list of questions and answers.
        exam_name (str): The name of the exam.
        difficulty (str): The difficulty level.
        file_name (str): The path to save the PDF file.
    """
    doc = SimpleDocTemplate(file_name, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(f"{exam_name.title()} Practice Paper", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    # Subtitle
    story.append(Paragraph(f"Difficulty Level: {difficulty.title()}", styles['h3']))
    story.append(Spacer(1, 0.25 * inch))

    # --- Questions Section ---
    story.append(Paragraph("Questions", styles['h2']))
    story.append(Spacer(1, 0.1 * inch))

    for i, item in enumerate(paper_data, 1):
        # Format the question number and text
        q_text = f"{i}. {item.question}"
        story.append(Paragraph(q_text, styles['BodyText']))
        story.append(Spacer(1, 0.1 * inch))

        # Format the options
        for key, value in item.options.items():
            option_text = f"&nbsp;&nbsp;&nbsp;&nbsp;{key}) {value}"
            story.append(Paragraph(option_text, styles['BodyText']))
        story.append(Spacer(1, 0.2 * inch))

    # --- Answer Key Section ---
    story.append(PageBreak())
    story.append(Paragraph("Answer Key", styles['h2']))
    story.append(Spacer(1, 0.2 * inch))

    for i, item in enumerate(paper_data, 1):
        answer_text = f"{i}. {item.answer}"
        story.append(Paragraph(answer_text, styles['BodyText']))

    doc.build(story)
    print(f"✅ PDF successfully generated and saved to: {os.path.abspath(file_name)}")


# --- Main Paper Generation Function ---
def generate_paper(name_of_the_exam: str, difficulty_level: str, format_of_the_exam: str, num_questions: int = 10):
    """
    Generates a paper, extracts the content, and saves it as a PDF.

    Args:
        name_of_the_exam (str): Name of the exam.
        difficulty_level (str): Difficulty level of the exam.
        format_of_the_exam (str): Format of the exam (e.g., "MCQ").
        num_questions (int): The number of questions to generate.

    Returns:
        str: Path to the generated PDF file, or None on failure.
    """
    try:
        # It's good practice to keep the client initialization separate.
        # Ensure you have your API key set correctly.
        client = genai.Client(api_key="AIzaSyDw1m0XtsBhoXFcgrWY9E2hTIKvHGHQkg4")

        # --- A more detailed and robust prompt ---
        prompt = (
            f"You are an expert question paper setter for competitive exams in India. "
            f"Your task is to create a high-quality practice paper for the '{name_of_the_exam.upper()}' exam. "
            f"The paper must be at a '{difficulty_level}' difficulty level and consist of {num_questions} "
            f"questions in '{format_of_the_exam}' format.\n\n"
            f"For each question, please provide:\n"
            f"1. A clear and unambiguous 'question'.\n"
            f"2. A dictionary of four 'options' labeled 'A', 'B', 'C', and 'D'.\n"
            f"3. The correct 'answer', which should be the key of the correct option (e.g., 'A').\n\n"
            f"Return the entire list of questions as a single, minified JSON array."
        )

        print("⏳ Generating paper content with the model...")
        response = client.generate_content(
            # Using a recommended model for this task
            model="models/gemini-1.5-flash",
            contents=prompt,
            generation_config={
                "response_mime_type": "application/json",
            }
        )
        print("✅ Content generated successfully.")

        # --- Extract and Parse the Response ---
        # The response text is a JSON string, so we parse it into a Python list.
        # We also validate it against our Pydantic model.
        raw_data = json.loads(response.text)
        paper_data = [QuestionAnswer(**item) for item in raw_data]

        # --- Generate the PDF ---
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        pdf_file_name = f"{name_of_the_exam.replace(' ', '_')}_{timestamp}.pdf"

        create_pdf(paper_data, name_of_the_exam, difficulty_level, pdf_file_name)

        return os.path.abspath(pdf_file_name)

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        # This can happen if the API key is invalid or the model's output isn't valid JSON.
        return None


# --- Main execution block ---
if __name__ == '__main__':
    # You can change these parameters to generate different papers
    generated_pdf_path = generate_paper(
        name_of_the_exam="JEE Mains Physics",
        difficulty_level="medium",
        format_of_the_exam="MCQ",
        num_questions=15
    )

    if generated_pdf_path:
        print(f"\nProcess finished. Your file is located at: {generated_pdf_path}")
    else:
        print("\nProcess failed. Please check the error messages above.")
