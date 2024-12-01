import os
import streamlit as st
import requests
import json
import time

# Get API key from environment or secrets
if st.secrets and 'XAI_API_KEY' in st.secrets:
    api_key = st.secrets['XAI_API_KEY']
else:
    api_key = os.getenv('XAI_API_KEY')

if not api_key:
    st.error("API key not found. Please set XAI_API_KEY in environment variables or Streamlit secrets.")
    st.stop()

# X.AI API configuration
XAI_BASE_URL = "https://api.x.ai/v1"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

def generate_question(level):
    """Generate a question based on the difficulty level"""
    try:
        # First try to generate a question using X.AI
        response = requests.post(
            f"{XAI_BASE_URL}/chat/completions",
            headers=headers,
            json={
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": "You are APPtitude, an intelligent math teacher. Generate a mental math questions related to Quantitative Apptitude, like time and distance, profit and loss, measurements, number series, etc. Make sure the question is suitable for the given difficulty level (1-5)."},
                    {"role": "user", "content": f"Generate a mental math question for difficulty level {level} (1=easiest, 5=hardest). Return ONLY a JSON object with the following format: {{\"question\": \"question text\", \"answer\": \"numerical answer\", \"explanation\": \"step-by-step solution\"}}"}
                ]
            }
        )
        
        response.raise_for_status()
        data = response.json()
        
        if 'choices' in data and len(data['choices']) > 0:
            content = data['choices'][0]['message']['content'].strip()
            try:
                start = content.find('{')
                end = content.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = content[start:end]
                    parsed_response = json.loads(json_str)
                    if all(key in parsed_response for key in ["question", "answer", "explanation"]):
                        return parsed_response
                raise Exception("Invalid response format")
            except (json.JSONDecodeError, ValueError) as e:
                raise Exception("Invalid response format")
        
    except Exception as e:
        # Use fallback questions when API fails
        fallback_questions = [
            {
                "question": "A train travels 360 kilometers in 4 hours. What is its average speed in kilometers per hour?",
                "answer": "90",
                "explanation": "Average speed = Total distance / Total time = 360 km / 4 hours = 90 km/h"
            },
            {
                "question": "A shopkeeper bought an item for ₹800 and sold it for ₹1000. What is the profit percentage?",
                "answer": "25",
                "explanation": "Profit = Selling Price - Cost Price = ₹1000 - ₹800 = ₹200\nProfit Percentage = (Profit / Cost Price) × 100 = (200 / 800) × 100 = 25%"
            },
            {
                "question": "Find the next number in the series: 2, 6, 12, 20, ?",
                "answer": "30",
                "explanation": "The pattern is adding consecutive even numbers: +4, +6, +8, +10\n2 + 4 = 6\n6 + 6 = 12\n12 + 8 = 20\n20 + 10 = 30"
            },
            {
                "question": "If 15 workers can complete a job in 12 days, how many days will it take for 20 workers to complete the same job?",
                "answer": "9",
                "explanation": "Using the formula: (Workers₁ × Days₁) = (Workers₂ × Days₂)\n15 × 12 = 20 × Days₂\n180 = 20 × Days₂\nDays₂ = 180 ÷ 20 = 9 days"
            },
            {
                "question": "A mixture contains milk and water in the ratio 5:3. If 4 liters of water is added, the ratio becomes 5:4. Find the initial quantity of milk in liters.",
                "answer": "20",
                "explanation": "Let initial milk be 5x and water be 3x\nAfter adding 4L water: 5x:(3x+4) = 5:4\n20x = 15x + 20\n5x = 20\nx = 4\nInitial milk = 5x = 5 × 4 = 20 liters"
            }
        ]
        return fallback_questions[level % len(fallback_questions)]

def check_answer(user_answer, correct_answer):
    """Check if the user's answer is correct"""
    try:
        # Try to convert answers to floats for numerical comparison
        user_float = float(user_answer.replace('$', '').strip())
        correct_float = float(correct_answer.replace('$', '').strip())
        
        # Check if answers are equal (with small tolerance for floating point)
        return abs(user_float - correct_float) < 0.01
    except ValueError:
        # If answers can't be converted to float, use string comparison
        return user_answer.strip().lower() == correct_answer.strip().lower()

def reset_answer_field():
    st.session_state.answer_input = ""

# Streamlit UI
st.set_page_config(
    page_title="APPtitude - Quantitative Aptitude Practice",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        height: 3rem;
        margin-top: 0.5rem;
    }
    .question-card {
        background-color: white;
        padding: 2rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    .explanation-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
    }
    .timer {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1f2937;
        text-align: center;
        padding: 1rem;
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .loading {
        text-align: center;
        padding: 2rem;
        font-size: 1.2rem;
        color: #6b7280;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
col1, col2 = st.columns([2, 1])
with col1:
    st.title("APPtitude - Quantitative Aptitude Practice")
    st.markdown("Master quantitative concepts through interactive practice: Time & Distance, Profit & Loss, Measurements, Number Series, and more!")

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
    if 'answer_input' in st.session_state:
        del st.session_state.answer_input

# Level selection dropdown
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

if selected_level != st.session_state.difficulty:
    st.session_state.difficulty = selected_level
    st.session_state.current_question = None
    st.session_state.show_explanation = False
    st.session_state.timer_start = None
    if 'answer_input' in st.session_state:
        del st.session_state.answer_input

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
    # Display timer
    if st.session_state.timer_start and not st.session_state.show_explanation:
        elapsed_time = int(time.time() - st.session_state.timer_start)
        st.markdown(f"""
            <div class='timer'>
                ⏱️ Time Elapsed: {format_time(elapsed_time)}
            </div>
        """, unsafe_allow_html=True)
    
    # Display question
    st.markdown("""
        <div class='question-card'>
            <h3>Question</h3>
            <p style='font-size: 1.2rem;'>{}</p>
        </div>
    """.format(st.session_state.current_question["question"]), unsafe_allow_html=True)
    
    if not st.session_state.show_explanation:
        # Answer section
        user_answer = st.text_input("Enter your answer:", key="answer_input", on_change=handle_answer_input)
        
        if st.button("Submit Answer", type="primary"):
            final_time = int(time.time() - st.session_state.timer_start)
            is_correct = check_answer(user_answer, st.session_state.current_question["answer"])
            
            if is_correct:
                st.success(f"🎉 Excellent! Your answer is correct! Time taken: {format_time(final_time)}")
                st.session_state.score += 1
            else:
                st.error(f"📝 Not quite right. The correct answer is {st.session_state.current_question['answer']}. Time taken: {format_time(final_time)}")
            
            st.session_state.total_questions += 1
            st.session_state.show_explanation = True
            st.session_state.timer_start = None
    
    # Show explanation and next button
    if st.session_state.show_explanation:
        st.markdown("""
            <div class='explanation-card'>
                <h3>Explanation</h3>
                <p>{}</p>
            </div>
        """.format(st.session_state.current_question["explanation"]), unsafe_allow_html=True)
        
        if st.button("Next Question", type="primary", on_click=next_question):
            pass

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
