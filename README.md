# Smart Exam & Classroom Management System

## Overview

The **Smart Exam & Classroom Management System** is a comprehensive web application designed to revolutionize how exams are generated, taken, and graded. Leveraging the power of **Google Gemini AI**, it allows teachers to create custom exams for various needs (School, Competitive) and provides an intelligent grading system for handwritten answers. Additionally, it features a robust classroom management system for seamless interaction between teachers and students.

## Features

### 🧠 AI-Powered Exam Generation

* **Customizable Exams**: Generate exams based on Subject, Grade, Board, Chapter, and Language.
* **Competitive Exams**: Create practice papers for competitive exams like JEE, NEET, etc., with adjustable difficulty levels.
* **Dual Modes**:
  * **Online Mode**: Take interactive quizzes directly on the platform.
  * **Offline Mode**: Download professionally formatted PDF question papers.

### 📝 AI Grading & Analytics

* **Handwritten Answer Grading**: Upload photos or PDFs of handwritten answer sheets.
* **Intelligent Evaluation**: Gemini AI analyzes the answers, compares them with the key, and provides a score along with detailed explanations.
* **Instant Feedback**: Get immediate results and performance insights.

### 🏫 Classroom Management

* **Role-Based Portals**: Dedicated dashboards for **Teachers** and **Students**.
* **Class Creation**: Teachers can create classrooms and invite students via unique codes.
* **Assignments**: Create, schedule, and track assignments.
* **Discussion**: Integrated posting and commenting system for class discussions.

### 🔔 Real-time Updates

* **Notifications**: Stay informed about new assignments, grades, and class updates.

## Tech Stack

* **Backend**: Python (Flask)
* **Database**: SQLite (SQLAlchemy)
* **AI Engine**: Google Gemini API (`google-genai`)
* **Frontend**: HTML, CSS, JavaScript (Jinja2 templates)
* **PDF Handling**: `fpdf2`, `PyPDF2`

## Prerequisites

* Python 3.8 or higher
* A Google Gemini API Key

## Installation

1. **Clone the Repository**

    ```bash
    git clone <repository-url>
    cd quizproject
    ```

2. **Create a Virtual Environment (Recommended)**

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3. **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4. **Set Up Environment Variables**
    * Create a `.env` file in the root directory.
    * Add your Gemini API Key:

        ```env
        GEMINI_API_KEY=your_api_key_here
        ```

    * Alternatively, you can place your key in a file named `apikey.txt` in the root directory.

## Usage

1. **Run the Application**

    ```bash
    python app.py
    ```

2. **Access the Web Interface**
    * Open your browser and navigate to `http://127.0.0.1:5000`.

3. **Getting Started**
    * **Sign Up**: Create an account as a 'Teacher' or 'Student'.
    * **Teacher**: Create a classroom, generate an exam, or post an assignment.
    * **Student**: Join a classroom using a code, take an online quiz, or download a practice paper.

## Project Structure

```
quizproject/
├── app.py                 # Main Flask application entry point
├── requirements.txt       # Python dependencies
├── src/                   # Source code for core logic
│   ├── generate_paper.py  # AI exam generation logic
│   ├── utils.py           # Helper functions
│   └── ...
├── templates/             # HTML templates for the frontend
├── static/                # Static assets (CSS, JS, Images)
├── instance/              # SQLite database storage
└── ...
```

## License

[MIT License](LICENSE)
