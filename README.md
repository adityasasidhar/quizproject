# Exam Generator

A Flask-based interface for generating and taking exams, with both online and offline modes.

## Features

- **Online Exam Mode**: Take exams directly in the browser with instant scoring
- **Offline Exam Mode**: Download exam papers and upload answers later
- **AI-Powered Answer Evaluation**: Uses Google Gemini to evaluate uploaded answer sheets
- **Multiple Exam Types**: Supports JEE Mains, JEE Advanced, and NEET UG exams
- **Customizable Difficulty**: Choose from easy, medium, or hard difficulty levels
- **Various Question Formats**: Supports MCQ, subjective, and mixed format exams

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd QuizProject
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Make sure you have a valid Google API key for Gemini in the `apikey.txt` file at the project root.

## Usage

1. Start the Flask application:
   ```
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

3. Choose between online and offline exam modes:
   - **Online Mode**: Take the exam in the browser and get instant results
   - **Offline Mode**: Download the exam paper and upload your answers later

## Online Exam Flow

1. Select "Online Exam" on the home page
2. Configure your exam:
   - Choose an exam type (JEE Mains, JEE Advanced, NEET UG)
   - Select difficulty level (easy, medium, hard)
   - Choose exam format (MCQ, subjective, mixed)
3. Click "Generate Exam" to create your exam
4. Answer the questions in the browser
5. Click "Submit Exam" when finished
6. View your results and feedback

## Offline Exam Flow

1. Select "Offline Exam" on the home page
2. Configure your exam (same options as online mode)
3. Click "Generate Exam" to create your exam
4. Download the exam paper using the provided button
5. Complete the exam on your own time
6. Return to the application and click "Upload Answers"
7. Upload a photo or scan of your completed answer sheet
8. View your results and feedback

## API Key Setup

The application requires a Google API key for Gemini to function properly:

1. Obtain an API key from the [Google AI Studio](https://makersuite.google.com/)
2. Create a file named `apikey.txt` in the project root directory
3. Paste your API key into this file (no additional text or whitespace)

## Project Structure

- `app.py`: Main Flask application
- `src/generate_paper.py`: Core functionality for generating exam papers
- `templates/`: HTML templates for the web interface
- `static/`: CSS and JavaScript files
- `GENERATED_PAPERS/`: Directory where generated exam papers are stored

## Dependencies

- Flask: Web framework
- Google Genai: AI functionality for paper generation and answer evaluation
- Pydantic: Data validation
- Bootstrap: Frontend styling (loaded via CDN)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini for AI capabilities
- Flask team for the excellent web framework
- Bootstrap team for the frontend components