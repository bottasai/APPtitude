import os
import streamlit as st
import requests
import json
import time
import random
import google.generativeai as genai
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
XAI_API_KEY = os.getenv('XAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not XAI_API_KEY or not GEMINI_API_KEY:
    st.error("API keys not found. Please check your .env file.")
    st.stop()

# Configure APIs
XAI_BASE_URL = "https://api.x.ai/v1"
xai_headers = {
    "Authorization": f"Bearer {XAI_API_KEY}",
    "Content-Type": "application/json"
}

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-pro')

# Define question types
QUESTION_TYPES = [
    "Time and Distance",
    "Profit and Loss",
    "Percentages",
    "Number Series",
    "Simple Interest",
    "Compound Interest",
    "Ratios and Proportions",
    "Averages",
    "Mixtures and Allegations",
    "Work and Time"
]

def get_random_question_type() -> str:
    """Randomly select a question type from the available types"""
    return random.choice(QUESTION_TYPES)

def generate_question_xai(level: int, question_type: str) -> Dict[str, Any]:
    """Generate a question using X.AI's Grok model"""
    try:
        # If Random is selected or there's an API error, choose a random type
        actual_type = get_random_question_type() if question_type == "Random" else question_type
        
        response = requests.post(
            f"{XAI_BASE_URL}/chat/completions",
            headers=xai_headers,
            json={
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": "You are APPtitude, an intelligent math teacher. Generate mental math questions related to Quantitative Aptitude, like time and distance, profit and loss, measurements, number series types. Make sure the question is suitable for the given difficulty level (1-5)."},
                    {"role": "user", "content": f"Generate a mental math question of type {actual_type} for difficulty level {level} (1=easiest, 5=hardest). Format your response as a valid JSON object with exactly these fields: question (string), answer (string with just the number), and explanation (string). Example: {{\"question\": \"What is 2+2?\", \"answer\": \"4\", \"explanation\": \"Adding 2 and 2 equals 4\"}}"}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Extract the content from the response
        content = result['choices'][0]['message']['content']
        
        # Clean up the content to ensure it's valid JSON
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        # Parse the JSON content
        question_data = json.loads(content)
        
        # Validate the required fields
        required_fields = ['question', 'answer', 'explanation']
        if not all(field in question_data for field in required_fields):
            raise ValueError("Missing required fields in response")
            
        return question_data
    except Exception as e:
        st.error(f"Error generating question with X.AI: {str(e)}")
        return generate_fallback_question(level)

def generate_question_gemini(level: int, question_type: str) -> Dict[str, Any]:
    """Generate a question using Google's Gemini model"""
    try:
        # If Random is selected or there's an API error, choose a random type
        actual_type = get_random_question_type() if question_type == "Random" else question_type
        
        prompt = f"""You are APPtitude, an intelligent math teacher. Generate a mental math question of type {actual_type} for difficulty level {level} (1=easiest, 5=hardest).
        The question should be related to Quantitative Aptitude topics like time and distance, profit and loss, measurements, or number series.
        Return ONLY a JSON object with this exact format: {{"question": "question text", "answer": "numerical answer", "explanation": "step-by-step solution"}}
        Make sure the answer is a numerical value that can be directly compared."""

        response = gemini_model.generate_content(prompt)
        
        # Extract JSON from response
        json_str = response.text
        # Clean up the response to ensure it's valid JSON
        json_str = json_str.strip().strip('`').strip('json')
        question_data = json.loads(json_str)
        return question_data
    except Exception as e:
        st.error(f"Error generating question with Gemini: {str(e)}")
        return generate_fallback_question(level)

def check_answer_xai(user_answer: str, question: str, correct_answer: str) -> bool:
    """Validate answer using X.AI's Grok model"""
    try:
        response = requests.post(
            f"{XAI_BASE_URL}/chat/completions",
            headers=xai_headers,
            json={
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": "You are a precise math validator. Your task is to compare two numerical answers and determine if they are equivalent, considering different formats and representations. Respond with ONLY 'true' or 'false'."},
                    {"role": "user", "content": f"Question: {question}\nUser answer: {user_answer}\nCorrect answer: {correct_answer}\n\nAre these answers equivalent? Consider different number formats and representations. Respond with ONLY 'true' or 'false'."}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            }
        )
        
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content'].strip().lower()
        
        # First try exact match with 'true' or 'false'
        if content == 'true':
            return True
        if content == 'false':
            return False
            
        # If not exact match, try fallback
        return check_answer_fallback(user_answer, correct_answer)
        
    except Exception as e:
        st.error(f"Error validating answer with X.AI: {str(e)}")
        return check_answer_fallback(user_answer, correct_answer)

def check_answer_gemini(user_answer: str, question: str, correct_answer: str) -> bool:
    """Validate answer using Google's Gemini model"""
    try:
        prompt = f"""Question: {question}
        User's answer: {user_answer}
        Correct answer: {correct_answer}
        
        Is the user's answer correct? Consider numerical equivalence and different formats.
        Return ONLY 'true' or 'false' as response."""

        response = gemini_model.generate_content(prompt)
        
        # Get the response content and convert to lowercase
        content = response.text.strip().lower()
        
        # Simple string matching
        return content == 'true'
        
    except Exception as e:
        print(f"Error in check_answer_gemini: {str(e)}")  # Debug log
        return check_answer_fallback(user_answer, correct_answer)

def check_answer_fallback(user_answer: str, correct_answer: str) -> bool:
    """Fallback answer validation using simple comparison"""
    try:
        # Remove any currency symbols and whitespace
        user_clean = user_answer.strip().replace('$', '').replace('₹', '').replace(',', '')
        correct_clean = correct_answer.strip().replace('$', '').replace('₹', '').replace(',', '')
        
        # Convert to float and compare
        user_float = float(user_clean)
        correct_float = float(correct_clean)
        
        # Allow for small floating-point differences
        return abs(user_float - correct_float) < 0.01
    except ValueError:
        # If conversion to float fails, do a case-insensitive string comparison
        return user_answer.strip().lower() == correct_answer.strip().lower()

def check_answer(user_answer: str, question: str, correct_answer: str) -> bool:
    """Check answer based on selected LLM"""
    llm_choice = st.session_state.llm_choice if 'llm_choice' in st.session_state else "X.AI (Grok)"
    
    if llm_choice == "X.AI (Grok)":
        return check_answer_xai(user_answer, question, correct_answer)
    else:
        return check_answer_gemini(user_answer, question, correct_answer)

def generate_fallback_question(level: int) -> Dict[str, Any]:
    """Generate a fallback question when API calls fail"""
    questions = {
        1: {"question": "What is 12 + 15?", "answer": "27", "explanation": "Simple addition: 12 + 15 = 27"},
        2: {"question": "What is 25% of 80?", "answer": "20", "explanation": "25% = 1/4, so 80 ÷ 4 = 20"},
        3: {"question": "If 3 shirts cost $60, how much do 5 shirts cost?", "answer": "100", "explanation": "Cost per shirt = $60 ÷ 3 = $20, so 5 shirts = $20 × 5 = $100"},
        4: {"question": "A train travels 120 km in 2 hours. What is its speed in km/h?", "answer": "60", "explanation": "Speed = Distance ÷ Time = 120 km ÷ 2 h = 60 km/h"},
        5: {"question": "If the ratio of boys to girls in a class is 3:4 and there are 21 boys, how many girls are there?", "answer": "28", "explanation": "If 3 parts = 21 boys, then 1 part = 7, so 4 parts (girls) = 28"}
    }
    return questions.get(level, questions[1])

def generate_question(level: int) -> Dict[str, Any]:
    """Generate a question based on selected LLM and difficulty level"""
    question_type = st.session_state.question_type if 'question_type' in st.session_state else "Random"
    llm_choice = st.session_state.llm_choice if 'llm_choice' in st.session_state else "X.AI (Grok)"
    
    if llm_choice == "X.AI (Grok)":
        return generate_question_xai(level, question_type)
    else:
        return generate_question_gemini(level, question_type)

# Initialize session state
if 'difficulty' not in st.session_state:
    st.session_state.difficulty = 1
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'total_questions' not in st.session_state:
    st.session_state.total_questions = 0
if 'show_explanation' not in st.session_state:
    st.session_state.show_explanation = False
if 'rate_limit_error' not in st.session_state:
    st.session_state.rate_limit_error = False
if 'timer_start' not in st.session_state:
    st.session_state.timer_start = None
if 'loading_question' not in st.session_state:
    st.session_state.loading_question = False
if 'question_number' not in st.session_state:
    st.session_state.question_number = 0
if 'question_type' not in st.session_state:
    st.session_state.question_type = "Random"
if 'llm_choice' not in st.session_state:
    st.session_state.llm_choice = "X.AI (Grok)"

# Modern CSS styling with subtle colors
st.markdown("""
    <style>
    /* Subtle color palette and variables */
    :root {
        --primary-color: #2563eb;
        --primary-light: #60a5fa;
        --primary-dark: #1e40af;
        --success-color: #059669;
        --error-color: #dc2626;
        --background-color: #f8fafc;
        --card-background: #ffffff;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --border-radius: 0.5rem;
        --transition: all 0.2s ease;
    }

    /* Global styles */
    .main {
        padding: 2rem;
        background: var(--background-color);
        color: var(--text-primary) !important;
        max-width: 1200px;
        margin: 0 auto;
    }

    /* Header styling */
    .app-header {
        text-align: center;
        padding: 1.5rem;
        background: white;
        border-radius: var(--border-radius);
        margin-bottom: 2rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .app-header h1 {
        color: var(--primary-color) !important;
        font-size: 2rem !important;
        font-weight: 600 !important;
        margin-bottom: 0.5rem !important;
    }

    .app-header p {
        color: var(--text-secondary) !important;
        font-size: 1.1rem !important;
        font-weight: 400;
    }

    /* Card styling */
    .question-card {
        background: var(--card-background);
        padding: 1.5rem;
        border-radius: var(--border-radius);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
        border: 1px solid rgba(0, 0, 0, 0.05);
    }

    .question-card h3 {
        color: var(--text-primary) !important;
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
    }

    .question-card p {
        color: var(--text-secondary) !important;
        font-size: 1.1rem !important;
        line-height: 1.6 !important;
    }

    /* Timer styling */
    .timer {
        font-family: 'SF Mono', 'Roboto Mono', monospace !important;
        font-size: 1.25rem !important;
        font-weight: 500 !important;
        color: var(--primary-color) !important;
        padding: 0.75rem !important;
        text-align: center !important;
        margin: 1rem 0 !important;
        background: rgba(37, 99, 235, 0.1) !important;
        border-radius: var(--border-radius);
    }

    /* Button styling */
    .stButton > button {
        width: 100%;
        padding: 0.75rem 1.5rem !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        color: white !important;
        background: var(--primary-color) !important;
        border: none !important;
        border-radius: var(--border-radius) !important;
        transition: var(--transition) !important;
    }

    .stButton > button:hover {
        background: var(--primary-dark) !important;
        transform: translateY(-1px);
    }

    /* Select box styling */
    .stSelectbox {
        margin-bottom: 1rem;
    }

    .stSelectbox > div > div {
        background: white !important;
        border-radius: var(--border-radius) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
    }

    .stSelectbox > div > div > div {
        color: var(--text-primary) !important;
        background: white !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
    }

    .stSelectbox > div > div[data-baseweb="select"] > div {
        background: white !important;
        color: var(--text-primary) !important;
    }

    .stSelectbox > div > div[data-baseweb="select"] > div > div {
        color: var(--text-primary) !important;
    }

    .stSelectbox > div > div[data-baseweb="popover"] > div {
        background: white !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
    }

    .stSelectbox > div > div[data-baseweb="popover"] > div > ul > li {
        background: white !important;
        color: var(--text-primary) !important;
    }

    .stSelectbox > div > div[data-baseweb="popover"] > div > ul > li:hover {
        background: var(--background-color) !important;
    }

    .stSelectbox > div > div[data-baseweb="popover"] > div > ul > li[aria-selected="true"] {
        background: var(--primary-color) !important;
        color: white !important;
    }

    /* Mobile-specific select box styling */
    @media (max-width: 768px) {
        .stSelectbox {
            margin-bottom: 0.75rem;
        }

        .stSelectbox > div > div {
            background: white !important;
            border: 1px solid rgba(0, 0, 0, 0.15) !important;
        }

        .stSelectbox > div > div > div {
            font-size: 0.9rem !important;
            padding: 0.5rem !important;
        }

        /* Ensure selected option is visible */
        .stSelectbox > div > div[data-baseweb="select"] > div {
            background: white !important;
            color: var(--text-primary) !important;
            font-weight: 500 !important;
        }

        /* Style dropdown options */
        .stSelectbox > div > div[data-baseweb="popover"] {
            margin-top: 0.25rem !important;
        }

        .stSelectbox > div > div[data-baseweb="popover"] > div {
            border-radius: var(--border-radius) !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        }

        .stSelectbox > div > div[data-baseweb="popover"] > div > ul > li {
            padding: 0.75rem !important;
            font-size: 0.9rem !important;
        }
    }

    /* Input field styling */
    .stTextInput > div > div > input {
        border-radius: var(--border-radius) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        padding: 0.75rem !important;
        font-size: 1rem !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
    }

    /* Success/Error message styling */
    .element-container:has(div[data-testid="stMarkdownContainer"]:has(div[class*="stAlert"][data-baseweb="notification"][kind="success"])) {
        background: #f0fdf4 !important;
        padding: 1rem !important;
        border-radius: var(--border-radius) !important;
        border: 1px solid #bbf7d0 !important;
    }

    .element-container:has(div[data-testid="stMarkdownContainer"]:has(div[class*="stAlert"][data-baseweb="notification"][kind="error"])) {
        background: #fef2f2 !important;
        padding: 1rem !important;
        border-radius: var(--border-radius) !important;
        border: 1px solid #fecaca !important;
    }

    /* Loading animation */
    .loading {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 1.5rem;
        background: var(--card-background);
        border-radius: var(--border-radius);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .loading::after {
        content: "";
        width: 1.5rem;
        height: 1.5rem;
        border: 2px solid var(--primary-light);
        border-top: 2px solid var(--primary-dark);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* Score display */
    .score-display {
        background: white;
        color: var(--text-primary) !important;
        padding: 1rem;
        border-radius: var(--border-radius);
        text-align: center;
        font-size: 1.1rem !important;
        font-weight: 500;
        margin: 1rem 0;
        border: 1px solid rgba(0, 0, 0, 0.05);
    }

    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .main {
            padding: 1rem;
        }

        .app-header {
            padding: 1rem;
        }

        .app-header h1 {
            font-size: 1.5rem !important;
        }

        .app-header p {
            font-size: 1rem !important;
        }

        .question-card {
            padding: 1rem;
        }

        .question-card h3 {
            font-size: 1.1rem !important;
        }

        .question-card p {
            font-size: 1rem !important;
        }

        .timer {
            font-size: 1.1rem !important;
        }

        .stButton > button {
            padding: 0.6rem 1rem !important;
            font-size: 0.9rem !important;
        }
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Updated header with subtle design
st.markdown("""
    <div class='app-header'>
        <h1>APPtitude</h1>
        <p>Master Quantitative Skills with Interactive Practice</p>
    </div>
""", unsafe_allow_html=True)

# Callback to handle answer input changes
def handle_answer_input():
    if 'answer_input' in st.session_state:
        current_answer = st.session_state.answer_input
        # Process the answer if needed

# Callback to handle next question
def next_question():
    st.session_state.loading_question = True
    st.session_state.current_question = generate_question(st.session_state.difficulty)
    st.session_state.show_explanation = False
    st.session_state.timer_start = time.time()
    st.session_state.loading_question = False
    st.session_state.question_number += 1  # Increment question number

# Level selection dropdown, question type selection, and LLM selection
col1, col2, col3 = st.columns(3)

with col1:
    st.session_state.difficulty = st.selectbox(
        "Select Difficulty Level",
        options=[1, 2, 3, 4, 5],
        index=st.session_state.difficulty - 1,
        format_func=lambda x: f"Level {x}",
        key="difficulty_select"
    )

with col2:
    st.session_state.question_type = st.selectbox(
        "Select Question Type",
        options=["Random"] + QUESTION_TYPES,
        index=0,
        key="question_type_select"
    )

with col3:
    llm_options = ["X.AI (Grok)", "Google Gemini"]
    selected_llm = st.selectbox(
        "Select AI Model",
        options=llm_options,
        key="llm_selector"
    )

if (st.session_state.difficulty != st.session_state.difficulty or 
    st.session_state.question_type != st.session_state.question_type or 
    selected_llm != st.session_state.llm_choice):
    st.session_state.difficulty = st.session_state.difficulty
    st.session_state.question_type = st.session_state.question_type
    st.session_state.llm_choice = selected_llm
    st.session_state.current_question = None
    st.session_state.show_explanation = False
    st.session_state.timer_start = None
    st.session_state.question_number = 0

# Main content area
st.markdown("---")

# Timer display
def format_time(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

# Question section
if st.session_state.loading_question:
    st.markdown("""
        <div class='loading'>
            <p>Loading next question...</p>
            <div class="stSpinner"></div>
        </div>
    """, unsafe_allow_html=True)

if not st.session_state.current_question:
    if st.button("Start Practice", type="primary", on_click=next_question):
        pass

# Display current question and timer
if st.session_state.current_question:
    try:
        # Display timer
        if st.session_state.timer_start and not st.session_state.show_explanation:
            elapsed_time = int(time.time() - st.session_state.timer_start)
            st.markdown(f"""
                <div class='timer'>
                    ⏱️ Time Elapsed: {format_time(elapsed_time)}
                </div>
            """, unsafe_allow_html=True)
        
        # Safely display question with error handling
        question_text = st.session_state.current_question.get("question", "")
        if not question_text:
            st.error("Error: Question not available. Generating new question...")
            next_question()
            st.rerun()
        
        st.markdown(f"""
            <div class='question-card'>
                <h3>Question</h3>
                <p>{question_text}</p>
            </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.show_explanation:
            # Answer section with dynamic key based on question number
            user_answer = st.text_input(
                "Enter your answer:", 
                key=f"answer_input_{st.session_state.question_number}",
                help="Type your answer and press Enter or click Submit"
            )
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Submit Answer", type="primary", use_container_width=True):
                    final_time = int(time.time() - st.session_state.timer_start)
                    is_correct = check_answer(user_answer, st.session_state.current_question["question"], st.session_state.current_question["answer"])
                    
                    if is_correct:
                        st.success(f"🎉 Excellent! Your answer is correct! Time: {format_time(final_time)}")
                        st.session_state.score += 1
                    else:
                        st.error(f"📝 Not quite right. Answer: {st.session_state.current_question['answer']}. Time: {format_time(final_time)}")
                    
                    st.session_state.total_questions += 1
                    st.session_state.show_explanation = True
                    st.session_state.timer_start = None
        
        # Show explanation and next button
        if st.session_state.show_explanation:
            explanation_text = st.session_state.current_question.get("explanation", "")
            if explanation_text:
                st.markdown(f"""
                    <div class='explanation-card'>
                        <h3>Explanation</h3>
                        <p>{explanation_text}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Next Question", type="primary", use_container_width=True):
                    next_question()
                    st.rerun()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}. Generating new question...")
        next_question()
        st.rerun()

# Sidebar with statistics
st.sidebar.markdown("### Your Progress")
if st.session_state.total_questions > 0:
    # Calculate statistics
    accuracy = (st.session_state.score / st.session_state.total_questions) * 100
    
    # Display metrics
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Total Questions", st.session_state.total_questions)
    col2.metric("Correct Answers", st.session_state.score)
    
    # Progress bar
    st.sidebar.markdown("### Accuracy")
    st.sidebar.progress(st.session_state.score / st.session_state.total_questions)
    st.sidebar.markdown(f"**{accuracy:.1f}%**")
    
    # Performance rating
    if accuracy >= 90:
        performance = "🌟 Outstanding!"
    elif accuracy >= 75:
        performance = "🎯 Very Good!"
    elif accuracy >= 60:
        performance = "👍 Good Progress"
    else:
        performance = "💪 Keep Practicing"
    
    st.sidebar.markdown(f"### Performance Rating\n{performance}")

# Reset button
def reset_progress():
    st.session_state.score = 0
    st.session_state.total_questions = 0
    st.session_state.current_question = None
    st.session_state.show_explanation = False
    st.session_state.timer_start = None
    st.session_state.question_number = 0  # Reset question number
    if 'answer_input' in st.session_state:
        del st.session_state.answer_input

if st.sidebar.button("Reset Progress", type="secondary", on_click=reset_progress):
    pass

# Tips section in sidebar
st.sidebar.markdown("""
    ### Quick Tips
    - Read each question carefully
    - Use paper for complex calculations
    - Practice regularly for better results
    - Review explanations to learn from mistakes
""")
