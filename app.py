import os
import streamlit as st
import requests
import json

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
                    {"role": "system", "content": "You are APPtitude, an intelligent math teacher. Generate a mental math question suitable for the given difficulty level (1-5)."},
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
                "question": "A train travels 240 kilometers in 3 hours. What is its average speed in kilometers per hour?",
                "answer": "80",
                "explanation": "Average speed = Total distance / Total time = 240 km / 3 hours = 80 km/h"
            },
            {
                "question": "If a shirt costs $45 and there's a 20% discount, what's the final price?",
                "answer": "36",
                "explanation": "20% of $45 = $45 × 0.2 = $9 discount. Final price = $45 - $9 = $36"
            },
            {
                "question": "A recipe needs 2.5 cups of flour to make 12 cookies. How many cups are needed for 30 cookies?",
                "answer": "6.25",
                "explanation": "For 30 cookies (2.5 × 30/12) = 2.5 × 2.5 = 6.25 cups"
            },
            {
                "question": "If you save $15 per week, how much will you save in 8 months (assuming 4 weeks per month)?",
                "answer": "480",
                "explanation": "8 months × 4 weeks × $15 = 32 weeks × $15 = $480"
            },
            {
                "question": "A car uses 6 liters of fuel per 100 kilometers. How many liters will it use for a 250km journey?",
                "answer": "15",
                "explanation": "Fuel needed = (250 km × 6 L) ÷ 100 km = 15 liters"
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

# Streamlit UI
st.set_page_config(
    page_title="APPtitude - Mental Math Practice",
    page_icon="🧮",
    layout="centered"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
    }
    .difficulty-section {
        padding: 1rem;
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("APPtitude - Mental Math Practice")
st.write("Improve your mental math skills with adaptive challenges!")

# Level selection in main content area
st.markdown("### Select Difficulty Level")
col1, col2, col3, col4, col5 = st.columns(5)

# Initialize difficulty in session state if not present
if 'difficulty' not in st.session_state:
    st.session_state.difficulty = 1

# Create level buttons
with col1:
    if st.button("Level 1", type="primary" if st.session_state.difficulty == 1 else "secondary"):
        st.session_state.difficulty = 1
with col2:
    if st.button("Level 2", type="primary" if st.session_state.difficulty == 2 else "secondary"):
        st.session_state.difficulty = 2
with col3:
    if st.button("Level 3", type="primary" if st.session_state.difficulty == 3 else "secondary"):
        st.session_state.difficulty = 3
with col4:
    if st.button("Level 4", type="primary" if st.session_state.difficulty == 4 else "secondary"):
        st.session_state.difficulty = 4
with col5:
    if st.button("Level 5", type="primary" if st.session_state.difficulty == 5 else "secondary"):
        st.session_state.difficulty = 5

st.markdown(f"**Current Level: {st.session_state.difficulty}**")

# Initialize session state for game management
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'total_questions' not in st.session_state:
    st.session_state.total_questions = 0
if 'show_explanation' not in st.session_state:
    st.session_state.show_explanation = False

# Question section
st.markdown("---")
if st.button("Get New Question"):
    st.session_state.current_question = generate_question(st.session_state.difficulty)
    st.session_state.show_explanation = False

if st.session_state.current_question:
    st.markdown("### Question")
    st.markdown(f"**{st.session_state.current_question['question']}**")
    
    # Answer section
    user_answer = st.text_input("Your Answer:", key="answer_input")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Submit Answer"):
            is_correct = check_answer(user_answer, st.session_state.current_question["answer"])
            
            if is_correct:
                st.success(" Correct! Well done!")
                st.session_state.score += 1
            else:
                st.error(f" Sorry, that's not correct. The correct answer is {st.session_state.current_question['answer']}")
            
            st.session_state.total_questions += 1
            st.session_state.show_explanation = True
    
    with col2:
        if st.button("Skip Question"):
            st.session_state.show_explanation = True
            st.session_state.total_questions += 1
    
    # Show explanation when answer is submitted or question is skipped
    if st.session_state.show_explanation:
        st.markdown("### Explanation")
        st.markdown(st.session_state.current_question["explanation"])

# Display score in sidebar
st.sidebar.markdown("### Your Progress")
if st.session_state.total_questions > 0:
    st.sidebar.markdown(f"**Score:** {st.session_state.score}/{st.session_state.total_questions}")
    accuracy = (st.session_state.score / st.session_state.total_questions) * 100
    st.sidebar.markdown(f"**Accuracy:** {accuracy:.1f}%")
    
    # Progress bar
    st.sidebar.progress(st.session_state.score / st.session_state.total_questions)

# Reset button in sidebar
if st.sidebar.button("Reset Progress"):
    st.session_state.score = 0
    st.session_state.total_questions = 0
    st.session_state.current_question = None
    st.session_state.show_explanation = False
