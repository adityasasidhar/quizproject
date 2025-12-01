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

BOOK_MAPPINGS = {
    "TSBIE": {
        "6": {
            "ENG": {
                "MATHEMATICS": {
                    "filename": "6th class maths em.pdf",
                    "chapters": [
                        "Knowing Our Numbers", "Whole Numbers", "Playing with Numbers", 
                        "Basic Geometrical Ideas", "Measures of Lines and Angles", "Integers", 
                        "Fractions and Decimals", "Data Handling", "Introduction to Algebra", 
                        "Perimeter and Area", "Ratio and Proportion", "Symmetry", 
                        "Practical Geometry", "Understanding 2D and 3D Shapes"
                    ]
                },
                "SCIENCE": {
                    "filename": "6th class gs em.pdf",
                    "chapters": [
                        "Our Food", "Playing with Magnets", "Rain: Where Does It Come From?", 
                        "What Do Animals Eat?", "Materials and Things", "Habitat", 
                        "Separation of Substances", "Fibre to Fabric", "Plants: Parts and Functions", 
                        "Changes Around Us", "Water in Our Life", "Simple Electric Circuits", 
                        "Learning How to Measure", "Movements in Animals", "Light, Shadows and Images", 
                        "Living and Nonliving"
                    ]
                },
                "SOCIAL": {
                    "filename": "6th social em.pdf",
                    "chapters": [
                        "Reading and Making Maps", "Globe – A Model of the Earth", 
                        "Land Forms – Penamakuru", "Dokur Village on the Plateau", 
                        "Penugolu – A Tribal Village", "From Gathering Food to Growing Food", 
                        "Agriculture in Our Times", "Trade in Agricultural Produce", 
                        "Community Decision Making in a Tribe", "Emergence of Kingdoms and Republics", 
                        "First Empires", "Democratic Government", "Village Panchayats", 
                        "Local Self – Government in Urban Areas", "Diversity in Our Society", 
                        "Towards Gender Equality", "Religion and Society in Early Times", 
                        "Devotion and Love towards God", "Language, Writing and Great Books", 
                        "Sculptures and Buildings", "Greenery in Telangana"
                    ]
                },
                "ENGLISH": {
                    "filename": "6th class english.pdf",
                    "chapters": [
                        "Peace and Harmony", "Telangana The Pride of the People", 
                        "What Can a Dollar and Eleven Cents Do?", "An Adventure", 
                        "Plant a Tree", "Rip Van Winkle", "P.T. Usha the Golden Girl", 
                        "Half the Price"
                    ]
                }
            },
            "TEL": {
                "TELUGU": {
                    "filename": "6th class telugu fl.pdf",
                    "chapters": [
                        "Abhinandana", "Snehabandham", "Varsham", "Lekha", "Shataka Sudha", 
                        "Pothana Balyam", "Udyama Spoorthi", "Chelimi", "Mamidi Chettu", 
                        "Ramzan", "Balanagamma", "Trijata Swapnam"
                    ]
                }
            },
            "HIN": {
                "HINDI": {
                    "filename": "6th hindi fl.pdf",
                    "chapters": [
                        "Aam Le Lo Aam!", "Hamara Gaon", "Railway Station", "Bazaar", 
                        "Mera Parivar", "Chidiyaghar", "Maidaan", "Baal Diwas", 
                        "Khushiyon Ki Duniya", "Hind Desh Ke Niwasi", "Udyan", 
                        "Bachche Chale Cricket Khelne", "Ye Path Kewal Padhne Ke Liye Hai", 
                        "Shabdkosh"
                    ]
                }
            }
        },
        "7": {
            "ENG": {
                "MATHEMATICS": {
                    "filename": "7th class maths em.pdf",
                    "chapters": [
                        "Integers", "Fractions, Decimals and Rational Numbers", "Simple Equations", 
                        "Lines and Angles", "Triangle and Its Properties", "Ratio - Applications", 
                        "Data Handling", "Congruency of Triangles", "Construction of Triangles", 
                        "Algebraic Expressions", "Powers and Exponents", "Quadrilaterals", 
                        "Area and Perimeter", "Understanding 3D and 2D Shapes", "Symmetry"
                    ]
                },
                "SCIENCE": {
                    "filename": "7th class gs em.pdf",
                    "chapters": [
                        "Food Components", "Acids and Bases", "Animal Fibre", "Motion and Time", 
                        "Heat - Measurement", "Weather and Climate", "Electricity", 
                        "Air, Winds and Cyclones", "Reflection of Light", "Nutrition in Plants", 
                        "Respiration in Organisms", "Reproduction in Plants", "Seed Dispersal", 
                        "Water", "Soil: Our Life", "Forest: Our Life", "Changes Around Us"
                    ]
                },
                "SOCIAL": {
                    "filename": "7th social em.pdf",
                    "chapters": [
                        "Reading Maps of Different Kinds", "Rain and Rivers", "Tanks and Ground Water", 
                        "Oceans and Fishing", "Europe", "Africa", "Handicrafts and Handlooms", 
                        "Industrial Revolution", "Production in a Factory - A Paper Mill", 
                        "Importance of Transport System", "New Kings and Kingdoms", 
                        "The Kakatiyas - Emergence of a Regional Kingdom", "The Kings of Vijayanagara", 
                        "Mughal Empire", "Establishment of British Empire in India", 
                        "Making of Laws in the State Assembly", "Implementation of Laws in the District", 
                        "Caste Discrimination and the Struggle for Equality", 
                        "Livelihood and Struggles of Urban Workers", "Folk - Religion", 
                        "Devotional Paths to the Divine", "Rulers and Buildings"
                    ]
                },
                "ENGLISH": {
                    "filename": "7th class english.pdf",
                    "chapters": [
                        "The Town Mouse and the Country Mouse", "C.V.Raman, the Pride of India", 
                        "Puru, the Brave", "Tenali Paints a Horse", "A Trip to Andaman", 
                        "A Hero", "The Wonderful World of Chess", "Snakes in India"
                    ]
                }
            }
        },
        "8": {
            "ENG": {
                "MATHEMATICS": {
                    "filename": "8EM_MAT.pdf",
                    "chapters": [
                        "Rational Numbers", "Linear Equations in One Variable", "Construction of Quadrilaterals", 
                        "Exponents and Powers", "Comparing Quantities using Proportion", 
                        "Square Roots and Cube Roots", "Frequency Distribution Tables and Graphs", 
                        "Exploring Geometrical Figures", "Area of Plane Figures", 
                        "Direct and Inverse Proportions", "Algebraic Expressions", "Factorisation", 
                        "Visualizing 3-D in 2-D", "Surface Areas and Volumes", "Playing with Numbers"
                    ]
                },
                "PHYSICS": {
                    "filename": "8EM_PHY.pdf",
                    "chapters": [
                        "Force", "Friction", "Synthetic Fibres and Plastics", "Metals and Non-metals", 
                        "Sound", "Reflection of Light at Plane Surface", "Coal and Petroleum", 
                        "Combustion, Fuels and Flame", "Electrical Conductivity of Liquids", 
                        "Some Natural Phenomena", "Stars and the Solar System", "Graphs of Motion"
                    ]
                },
                "BIOLOGY": {
                    "filename": "8EM_BIO.pdf",
                    "chapters": [
                        "What is Science?", "Cell - The Basic Unit of Life", "Microbial World", 
                        "Reproduction in Animals", "Adolescence", "Biodiversity and its Conservation", 
                        "Different Ecosystems", "Food Production from Plants", 
                        "Food Production from Animals", "Why do we fall ill?", 
                        "Not to Drink - Not to Breath"
                    ]
                },
                "SOCIAL": {
                    "filename": "8EM_SOC.pdf",
                    "chapters": [
                        "Reading and Analysis of Maps", "Energy from the Sun", "Earth Movements and Seasons", 
                        "The Polar Regions", "Forests: Using and Protecting Them", "Minerals and Mining", 
                        "Money and Banking", "Impact of Technology on Livelihoods", 
                        "Public Health and the Government", "Landlords and Tenants under the British and the Nizam", 
                        "National Movement - The Early Phase", "National Movement - The Last Phase", 
                        "Freedom Movement in Hyderabad State", "The Indian Constitution", 
                        "Parliament and Central Government", "Law and Justice - A Case Study", 
                        "Abolition of Zamindari System", "Understanding Poverty", "Rights Approach to Development", 
                        "Social and Religious Reform Movements", "Understanding Secularism", 
                        "Performing Arts and Artistes in Modern Times", "Film and Print Media", 
                        "Sports: Nationalism and Commerce", "Disaster Management"
                    ]
                },
                "ENGLISH": {
                    "filename": "8_ENG.pdf",
                    "chapters": [
                        "The Tattered Blanket", "Oliver Asks for More", "The Selfish Giant", 
                        "The Fun They Had", "Bonsai Life", "Gratitude"
                    ]
                }
            }
        },
        "9": {
            "ENG": {
                "BIOLOGY": {
                    "filename": "ENG/9_BIOLOGY_MERGED.pdf",
                    "chapters": [
                        "Cell its structure and functions", "Plant tissues", "Animal tissues", 
                        "Plasma membrane", "Diversity in Living Organisms", "Sense Organs", 
                        "Animal behaviour", "Challenges in Improving Agricultural Products", 
                        "Adaptations in Different Ecosystems", "Soil pollution", "Biogeochemical cycles"
                    ]
                },
                "PHYSICS": {
                    "filename": "ENG/9_PHYSICS_MERGED.pdf",
                    "chapters": [
                        "Matter Around Us", "Motion", "Laws of Motion", "Refraction of Light at Plane Surfaces", 
                        "Gravitation", "Is Matter Pure?", "Atoms and Molecules and Chemical Reactions", 
                        "Floating Bodies", "What is inside the Atom?", "Work and Energy", "Heat", "Sound"
                    ]
                }
            }
        },
        "10": {
            "ENG": {
                "ENVIRONMENTAL EDUCATION": {
                    "filename": "10 env edn em 2021.pdf",
                    "chapters": [
                        "Global warming", "Saviours of our environment", "Estimation of particulate pollutants in air", 
                        "Vaccination - A shield", "Mosquitoes - woes", "Fossil fuels", 
                        "Changes in surroundings and their effect", "Use solar energy - Save electricity", 
                        "Pollination - an interaction of plants and insects", "Observing 4 'R's", 
                        "Conserving natural resources", "Over use of groundwater - it's consequences", 
                        "Impact of low-cost materials on environment", "Urbanization - employment opportunities", 
                        "Plenty of water - still we are thirsty!", "Do we need zoos?", 
                        "Nature, culture, people and their relationships", "Household Wastes", 
                        "The plight of ragpickers", "Water bodies in the neighbourhood", 
                        "Impact assessment of developmental projects", "Awareness about common ailments", 
                        "Disaster management", "Education for all - Everybody's concern", 
                        "Let's keep our domestic environment healthy", "Depletion of natural resources", 
                        "Conservation of water resources", "Flourosis", "Nature is a sacred place"
                    ]
                },
                "SOCIAL": {
                    "filename": "10 social em-21.pdf",
                    "chapters": [
                        "India: Relief Features", "Ideas of Development", "Production and Employment", 
                        "Climate of India", "Indian Rivers and Water Resources", "The Population", 
                        "Settlements - Migrations", "Rampur: A Village Economy", "Globalisation", 
                        "Food Security", "Sustainable Development with Equity", 
                        "World Between the World Wars", "National Liberation Movements in the Colonies", 
                        "National Movement in India - Partition & Independence", 
                        "The Making of Independent India's Constitution", "Election Process in India", 
                        "Independent India (The First 30 years)", "Emerging Political Trends", 
                        "Post - War World and India", "Social Movements in Our Times", 
                        "The Movement for the Formation of Telangana State"
                    ]
                }
            }
        }
    }
}

def get_available_books():
    """
    Scans the CONTENT/BOOKS directory and returns a nested dictionary structure:
    Board -> Grade -> Language -> Subject -> [Chapters]
    Uses BOOK_MAPPINGS if available, otherwise falls back to directory scanning.
    """
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CONTENT", "BOOKS")
    structure = {}

    if not os.path.exists(base_dir):
        return structure

    for board in os.listdir(base_dir):
        board_path = os.path.join(base_dir, board)
        if not os.path.isdir(board_path):
            continue
        
        structure[board] = {}
        
        for grade in os.listdir(board_path):
            grade_path = os.path.join(board_path, grade)
            if not os.path.isdir(grade_path):
                continue
            
            # Check if we have a mapping for this Board/Grade
            if board in BOOK_MAPPINGS and grade in BOOK_MAPPINGS[board]:
                structure[board][grade] = {}
                mapped_grade = BOOK_MAPPINGS[board][grade]
                
                for lang, subjects in mapped_grade.items():
                    structure[board][grade][lang] = {}
                    for subj, details in subjects.items():
                        # Verify file exists before adding
                        # The file is expected to be directly in the grade folder for TSBIE/6
                        # or in a subfolder? The user said "CONTENT/BOOKS/TSBIE/6/filename.pdf"
                        # So we check os.path.join(grade_path, details['filename'])
                        
                        file_path = os.path.join(grade_path, details['filename'])
                        if os.path.exists(file_path):
                            structure[board][grade][lang][subj] = details['chapters']
            else:
                # Fallback to directory scanning
                structure[board][grade] = {}
                for item in os.listdir(grade_path):
                    item_path = os.path.join(grade_path, item)
                    
                    if os.path.isdir(item_path):
                        lang = item
                        structure[board][grade][lang] = {}
                        
                        for subject in os.listdir(item_path):
                            subject_path = os.path.join(item_path, subject)
                            if os.path.isdir(subject_path):
                                chapters = [f for f in os.listdir(subject_path) if f.lower().endswith('.pdf')]
                                structure[board][grade][lang][subject] = chapters
    
    return structure

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

        # Determine exam subdirectory from JSON path
        exam_subdir = "MISC"
        parts = os.path.normpath(filepath).split(os.sep)
        for candidate in ("MAINS", "ADVANCED", "NEET"):
            if candidate in parts:
                exam_subdir = candidate
                break

        # Ensure papers output directory exists
        papers_dir = os.path.join("PAPERS", exam_subdir)
        os.makedirs(papers_dir, exist_ok=True)

        # Base name for PDFs derived from JSON filename (already unique due to timestamp)
        base_name = os.path.splitext(os.path.basename(filepath))[0]

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

        question_pdf_path = os.path.join(papers_dir, f"{base_name}_questions.pdf")
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

        answer_pdf_path = os.path.join(papers_dir, f"{base_name}_answers.pdf")
        answer_pdf.output(answer_pdf_path)

        return question_pdf_path, answer_pdf_path

