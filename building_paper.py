import os
import json
import time
import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.generativeai.types import GenerationConfig
from PyPDF2 import PdfReader

genai.configure(api_key="AIzaSyDw1m0XtsBhoXFcgrWY9E2hTIKvHGHQkg4")

class NEETPaperGenerator:
    def __init__(self, papers_dir="NEET"):
        self.papers_dir = papers_dir
        self.model = GenerativeModel("gemini-2.5-flash")
        print("Loading the Previous Year papers")
        self.previous_papers = self.load_papers()

    def load_papers(self):
        """Load and read previous NEET papers from the directory (text or PDF)."""
        papers = []
        try:
            for filename in os.listdir(self.papers_dir):
                file_path = os.path.join(self.papers_dir, filename)
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

    def generate_question_paper(self, difficulty="medium", num_questions=180):
        """Generate a new NEET question paper based on difficulty and number of questions."""
        print("Generating Question papers")
        if not self.previous_papers:
            print("No previos year ")
            return "No previous papers available to generate a new paper."

        # Define prompt based on difficulty
        difficulty_prompt = {
            "easy": "Generate simple and straightforward questions suitable for beginners preparing for NEET.",
            "medium": "Generate moderately challenging questions that test a good understanding of NEET syllabus topics.",
            "hard": "Generate complex and challenging questions that require deep understanding and application of NEET syllabus topics."
        }

        prompt = f"""
        You are an expert in creating NEET (National Eligibility cum Entrance Test) question papers. 
        Based on the following previous NEET papers: {self.previous_papers[:2]}, 
        generate a new NEET question paper with {num_questions} questions. 
        The difficulty level should be {difficulty}: {difficulty_prompt.get(difficulty, 'medium')}.
        The paper should cover Physics, Chemistry, and Biology (Botany and Zoology) in the standard NEET format (45 questions each for Physics and Chemistry, 90 for Biology).
        Provide the output in a structured JSON format with question text, options (a, b, c, d), and correct answer.
        Ensure the questions are unique and not copied from the provided papers.
        Example output format:
        [
            {{
                "question": "Sample question text?",
                "options": {{"a": "Option A", "b": "Option B", "c": "Option C", "d": "Option D"}},
                "correct_answer": "a",
                "subject": "Physics"
            }}
        ]
        Ensure the JSON is valid and complete, with proper string escaping and no trailing commas.
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=16384,  # Increased to handle full paper
                    response_mime_type="application/json"
                )
            )
            # Debug: Save raw response to file for inspection
            with open("raw_response.txt", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("Raw API response saved to raw_response.txt")
            # Validate JSON before parsing
            try:
                json_data = json.loads(response.text)
                return json_data
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Raw response (first 1000 chars): {response.text[:1000]}...")
                return []
        except Exception as e:
            print(f"Error generating question paper: {e}")
            return []

    def save_paper(self, paper_data, output_file="new_neet_paper.json"):
        """Save the generated question paper to a file."""
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(paper_data, f, indent=4)
            print(f"Question paper saved to {output_file}")
        except Exception as e:
            print(f"Error saving paper: {e}")

    def generate_and_download(self, difficulty="medium", num_questions=180):
        """Generate a new paper and save it for download."""
        paper = self.generate_question_paper(difficulty, num_questions)
        if paper:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"neet_paper_{difficulty}_{timestamp}.json"
            self.save_paper(paper, output_file)
            return output_file
        return None

if __name__ == "__main__":
    generator = NEETPaperGenerator()
    output_file = generator.generate_and_download(difficulty="medium")
    if output_file:
        print(f"New NEET paper generated and saved as {output_file}")