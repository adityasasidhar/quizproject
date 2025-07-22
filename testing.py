import os
import json
import time
# The user's environment uses this import pattern
from google import genai
from pydantic import BaseModel

# --- Configuration ---
# Initialize the client by passing the API key directly, as per the documentation you found.
try:
    # IMPORTANT: Use your actual API key here.
    client = genai.Client(api_key="AIzaSyDw1m0XtsBhoXFcgrWY9E2hTIKvHGHQkg4")
except TypeError as e:
    print(f"❌ Client Initialization Error: {e}")
    print("This might mean your library is very old. Try running 'pip install --upgrade google-generativeai'")
    exit()
except Exception as e:
    print(f"❌ An unexpected error occurred during client initialization: {e}")
    exit()

class PaperGenerator(BaseModel):
    """Defines the structure for a single question and its corresponding answer."""
    question: str
    answer: str

def generate_paper(client: genai.Client, name_of_the_exam: str, difficulty_level: str, format_of_the_exam: str, num_questions: int = 10):
    """
    Generates an exam paper using the Gemini API and saves it as a text file.

    Args:
        client (genai.Client): The initialized GenAI client.
        name_of_the_exam (str): The subject or name of the exam.
        difficulty_level (str): The difficulty level of the exam.
        format_of_the_exam (str): The type of questions.
        num_questions (int): The number of questions to generate.

    Returns:
        str: The absolute path to the generated text file, or None if an error occurred.
    """
    try:
        # 1. Create a dynamic prompt with instructions to format the output as JSON.
        prompt = (
            f"Generate {num_questions} {format_of_the_exam} questions for a "
            f"{name_of_the_exam} exam at a {difficulty_level} difficulty level. "
            f"For each item, provide a 'question' and its 'answer'. "
            f"Return the entire list as a single JSON array."
        )

        # 2. Call the API using the client.models.generate_content method
        response = client.generate_content(
            # Using the model name from your snippet
            model="models/gemini-1.5-flash",
            contents=prompt,
            generation_config={
                "response_mime_type": "application/json",
            }
        )

        # 3. Parse the JSON response from the model
        paper_data = json.loads(response.text)

        # 4. Validate the response against the Pydantic model (optional but good practice)
        validated_data = [PaperGenerator(**item) for item in paper_data]


        # 5. Format the questions and answers into a clear, readable layout
        paper_content = f"Exam Topic: {name_of_the_exam.title()}\n"
        paper_content += f"Difficulty: {difficulty_level.title()}\n"
        paper_content += f"Format: {format_of_the_exam.title()}\n"
        paper_content += "=" * 60 + "\n\n"

        for i, item in enumerate(validated_data, 1):
            paper_content += f"Question {i}:\n{item.question}\n\n"
            paper_content += f"Answer {i}:\n{item.answer}\n\n"
            paper_content += "-" * 60 + "\n\n"

        # 6. Save the content to a text file with a unique name
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        file_name = f"{name_of_the_exam.replace(' ', '_')}_{timestamp}.txt"

        with open(file_name, 'w', encoding='utf-8') as paper_file:
            paper_file.write(paper_content)

        file_path = os.path.abspath(file_name)
        print(f"✅ Paper successfully generated and saved to: {file_path}")
        return file_path

    except Exception as e:
        print(f"❌ An error occurred while generating the paper: {e}")
        return None

# --- Example of How to Use the Function ---
if __name__ == '__main__':
    # We now pass the 'client' object we created above into our function.
    generate_paper(
        client=client,
        name_of_the_exam="Introduction to Python",
        difficulty_level="easy",
        format_of_the_exam="multiple choice"
    )