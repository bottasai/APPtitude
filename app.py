import os
import streamlit as st
import requests
import json
import time
import google.generativeai as genai
from typing import Dict, Any

# Load environment variables
XAI_API_KEY = os.getenv('XAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure APIs
XAI_BASE_URL = "https://api.x.ai/v1"
xai_headers = {
    "Authorization": f"Bearer {XAI_API_KEY}",
    "Content-Type": "application/json"
}

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-pro')

def generate_question_xai(level: int, question_type: str) -> Dict[str, Any]:
    """Generate a question using X.AI's Grok model"""
    try:
        type_prompt = f"of type {question_type}" if question_type != "Random" else "randomly selected from different types"
        
        response = requests.post(
            f"{XAI_BASE_URL}/chat/completions",
            headers=xai_headers,
            json={
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": "You are APPtitude, an intelligent math teacher. Generate a mental math questions related to Quantitative Apptitude, like time and distance, profit and loss, measurements, number series types. Make sure the question is suitable for the given difficulty level (1-5). and questions must be randomly across the different types mentioned"},
                    {"role": "user", "content": f"Generate a mental math question {type_prompt} for difficulty level {level} (1=easiest, 5=hardest). Return ONLY a JSON object with the following format: {{\"question\": \"question text\", \"answer\": \"numerical answer\", \"explanation\": \"step-by-step solution\"}}"}
                ]
            }
        )
        
        response.raise_for_status()
        result = response.json()
        question_data = json.loads(result['choices'][0]['message']['content'])
        return question_data
    except Exception as e:
        st.error(f"Error generating question with X.AI: {str(e)}")
        return generate_fallback_question(level)

def generate_question_gemini(level: int, question_type: str) -> Dict[str, Any]:
    """Generate a question using Google's Gemini model"""
    try:
        type_prompt = f"of type {question_type}" if question_type != "Random" else "randomly selected from different types"
        
        prompt = f"""You are APPtitude, an intelligent math teacher. Generate a mental math question {type_prompt} for difficulty level {level} (1=easiest, 5=hardest).
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
                    {"role": "system", "content": "You are APPtitude, an intelligent math teacher evaluating student answers. answers can have other details along with the number value, so carefully understand the answer and question, instead of literally looking for the exact value."},
                    {"role": "user", "content": f"""Question: {question}
                    User's answer: {user_answer}
                    Correct answer: {correct_answer}
                    
                    Evaluate if the user's answer is correct and return ONLY a JSON object with this format:
                    {{"is_correct": true/false}}"""}
                ]
            }
        )
        
        response.raise_for_status()
        result = response.json()
        validation_result = json.loads(result['choices'][0]['message']['content'])
        return validation_result.get('is_correct', False)
    except Exception as e:
        st.error(f"Error validating answer with X.AI: {str(e)}")
        return check_answer_fallback(user_answer, correct_answer)

def check_answer_gemini(user_answer: str, question: str, correct_answer: str) -> bool:
    """Validate answer using Google's Gemini model"""
    try:
        prompt = f"""Question: {question}
        User's answer: {user_answer}
        Correct answer: {correct_answer}
        
        Evaluate if the user's answer is correct. Consider numerical equivalence and different formats of expressing the same value.
        Return ONLY a JSON object with this format: {{"is_correct": true/false}}"""

        response = gemini_model.generate_content(prompt)
        
        # Extract JSON from response
        json_str = response.text.strip().strip('`').strip('json')
        validation_result = json.loads(json_str)
        return validation_result.get('is_correct', False)
    except Exception as e:
        st.error(f"Error validating answer with Gemini: {str(e)}")
        return check_answer_fallback(user_answer, correct_answer)

def check_answer_fallback(user_answer: str, correct_answer: str) -> bool:
    """Fallback answer validation using simple comparison"""
    try:
        user_float = float(user_answer.strip())
        correct_float = float(correct_answer.strip())
        return abs(user_float - correct_float) < 0.01
    except ValueError:
        return user_answer.strip().lower() == correct_answer.strip().lower()

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

def check_answer(user_answer: str, question: str, correct_answer: str) -> bool:
    """Check answer based on selected LLM"""
    llm_choice = st.session_state.llm_choice if 'llm_choice' in st.session_state else "X.AI (Grok)"
    
    if llm_choice == "X.AI (Grok)":
        return check_answer_xai(user_answer, question, correct_answer)
    else:
        return check_answer_gemini(user_answer, question, correct_answer)

# Get API key from environment or secrets
if st.secrets and 'XAI_API_KEY' in st.secrets:
    api_key = st.secrets['XAI_API_KEY']
else:
    api_key = os.getenv('XAI_API_KEY')

if not api_key:
    st.error("API key not found. Please set XAI_API_KEY in environment variables or Streamlit secrets.")
    st.stop()

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
    levels = {
        1: "Level 1 - Basic Calculations",
        2: "Level 2 - Simple Applications",
        3: "Level 3 - Complex Problems",
        4: "Level 4 - Advanced Concepts",
        5: "Level 5 - Expert Challenges"
    }

    selected_level = st.selectbox(
        "Select Difficulty Level",
        options=list(levels.keys()),
        format_func=lambda x: levels[x],
        key="level_selector"
    )

with col2:
    question_types = [
        "Random",
        "Time and Distance",
        "Profit and Loss",
        "Number Series",
        "Time and Work",
        "Ratios and Mixtures",
        "Measurements"
    ]
    
    selected_type = st.selectbox(
        "Select Question Type",
        options=question_types,
        key="type_selector"
    )

with col3:
    llm_options = ["X.AI (Grok)", "Google Gemini"]
    selected_llm = st.selectbox(
        "Select AI Model",
        options=llm_options,
        key="llm_selector"
    )

if (selected_level != st.session_state.difficulty or 
    selected_type != st.session_state.question_type or 
    selected_llm != st.session_state.llm_choice):
    st.session_state.difficulty = selected_level
    st.session_state.question_type = selected_type
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

# Custom CSS for professional styling and mobile responsiveness
st.markdown("""
    <style>
    .main {
        padding: 1rem;
        color: #1f2937 !important;
    }
    .stApp {
        background-color: #f3f4f6;
    }
    @media (max-width: 768px) {
        .main {
            padding: 0.5rem;
        }
        .stButton>button {
            width: 100% !important;
            margin: 0.25rem 0 !important;
        }
        .row-widget.stSelectbox {
            margin-bottom: 1rem;
        }
    }
    .stButton>button {
        width: 100%;
        height: 3rem;
        margin-top: 0.5rem;
    }
    .question-card {
        background-color: #ffffff !important;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin: 0.75rem 0;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    .question-card h3 {
        color: #1f2937 !important;
        margin-bottom: 1rem !important;
        font-size: 1.25rem !important;
    }
    .question-card p {
        color: #374151 !important;
        font-size: 1.1rem !important;
        line-height: 1.5 !important;
    }
    .explanation-card {
        background-color: #f8f9fa !important;
        padding: 1.25rem;
        border-radius: 0.5rem;
        margin-top: 0.75rem;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    .explanation-card h3 {
        color: #1f2937 !important;
        margin-bottom: 0.75rem !important;
        font-size: 1.25rem !important;
    }
    .explanation-card p {
        color: #374151 !important;
        line-height: 1.5 !important;
    }
    .timer {
        font-size: 1.25rem;
        font-weight: bold;
        color: #1f2937 !important;
        text-align: center;
        padding: 0.75rem;
        background-color: #e5e7eb !important;
        border-radius: 0.5rem;
        margin: 0.75rem 0;
    }
    .loading {
        text-align: center;
        padding: 1.5rem;
        font-size: 1.1rem;
        color: #4b5563 !important;
    }
    .app-header {
        text-align: center;
        margin-bottom: 1rem;
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    .app-header h1 {
        color: #1f2937 !important;
        font-size: 2rem !important;
        margin-bottom: 0.5rem !important;
    }
    .app-header p {
        color: #4b5563 !important;
        font-size: 1.1rem !important;
    }
    @media (max-width: 768px) {
        .app-header h1 {
            font-size: 1.5rem !important;
        }
        .app-header p {
            font-size: 0.9rem !important;
        }
        .question-card, .explanation-card {
            padding: 1rem;
            margin: 0.5rem 0;
            background-color: #ffffff !important;
        }
        .question-card p {
            color: #374151 !important;
            font-size: 1rem !important;
        }
        .timer {
            font-size: 1rem;
            padding: 0.5rem;
            background-color: #e5e7eb !important;
            color: #1f2937 !important;
        }
    }
    div[data-testid="stToolbar"] {
        display: none;
    }
    .stTextInput>div>div>input {
        color: #1f2937 !important;
        background-color: #ffffff !important;
    }
    .stTextInput>label {
        color: #374151 !important;
    }
    .stMarkdown {
        color: #1f2937 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Header with responsive design
st.markdown("""
    <div class='app-header'>
        <h1>APPtitude - Quantitative Aptitude Practice</h1>
        <p>Master quantitative concepts through interactive practice</p>
    </div>
""", unsafe_allow_html=True)
