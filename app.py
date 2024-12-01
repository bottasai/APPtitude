import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import json
import streamlit as st

app = Flask(__name__)

# Initialize OpenAI client
if st.secrets and 'XAI_API_KEY' in st.secrets:
    api_key = st.secrets['XAI_API_KEY']
else:
    api_key = os.getenv('XAI_API_KEY')

if not api_key:
    raise ValueError("API key not found. Please set XAI_API_KEY in environment variables or Streamlit secrets.")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1"
)

def generate_question(level):
    """Generate a question based on the difficulty level"""
    try:
        # First try to generate a question using X.AI
        completion = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": "You are APPtitude, an intelligent math teacher. Generate a mental math question suitable for the given difficulty level (1-5)."},
                {"role": "user", "content": f"Generate a mental math question for difficulty level {level} (1=easiest, 5=hardest). Return ONLY a JSON object with the following format: {{\"question\": \"question text\", \"answer\": \"numerical answer\", \"explanation\": \"step-by-step solution\"}}"}
            ]
        )
        
        response = completion.choices[0].message.content.strip()
        print(f"API Response: {response}")  # Debug log
        
        # Try to extract JSON from the response
        try:
            # Find the JSON object in the response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = response[start:end]
                parsed_response = json.loads(json_str)
                if all(key in parsed_response for key in ["question", "answer", "explanation"]):
                    return json.dumps(parsed_response)
            raise Exception("Invalid response format")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parsing error: {str(e)}")
            raise Exception("Invalid response format")
        
    except Exception as e:
        print(f"Error generating question: {str(e)}")
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
        fallback = fallback_questions[level % len(fallback_questions)]
        return json.dumps(fallback)

def check_answer(question, user_answer, correct_answer, explanation):
    """Check if the user's answer is correct"""
    try:
        # First try to validate using X.AI
        completion = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": "You are APPtitude, an intelligent math teacher evaluating student answers."},
                {"role": "user", "content": f"""Question: {question}
                User's answer: {user_answer}
                Correct answer: {correct_answer}
                
                Evaluate if the user's answer is correct and return ONLY a JSON object with this format:
                {{
                    "is_correct": true/false,
                    "feedback": "explanation of why correct/incorrect",
                    "correct_answer": "{correct_answer}",
                    "explanation": "{explanation}"
                }}"""}
            ]
        )
        
        response = completion.choices[0].message.content.strip()
        print(f"API Response: {response}")  # Debug log
        
        # Try to extract JSON from the response
        try:
            # Find the JSON object in the response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = response[start:end]
                parsed_response = json.loads(json_str)
                if all(key in parsed_response for key in ["is_correct", "feedback", "correct_answer", "explanation"]):
                    return json.dumps(parsed_response)
            raise Exception("Invalid response format")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parsing error: {str(e)}")
            raise Exception("Invalid response format")
        
    except Exception as e:
        print(f"Error checking answer: {str(e)}")
        # Fallback to simple validation
        try:
            # Try to convert answers to floats for numerical comparison
            user_float = float(user_answer.replace('$', '').strip())
            correct_float = float(correct_answer.replace('$', '').strip())
            
            # Check if answers are equal (with small tolerance for floating point)
            is_correct = abs(user_float - correct_float) < 0.01
            
            response = {
                "is_correct": is_correct,
                "feedback": "Correct! Well done!" if is_correct else "Sorry, that's not correct.",
                "correct_answer": correct_answer,
                "explanation": explanation
            }
            
            return json.dumps(response)
            
        except ValueError:
            # If answers can't be converted to float, use string comparison
            is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
            response = {
                "is_correct": is_correct,
                "feedback": "Correct! Well done!" if is_correct else "Sorry, that's not correct.",
                "correct_answer": correct_answer,
                "explanation": explanation
            }
            return json.dumps(response)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_question', methods=['POST'])
def get_question():
    try:
        level = request.json.get('level', 1)
        response = generate_question(level)
        
        # Ensure response is proper JSON
        if isinstance(response, str):
            try:
                json.loads(response)  # Validate JSON
            except json.JSONDecodeError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid response format"
                }), 500
        
        return jsonify({
            "status": "success",
            "data": response
        })
    except Exception as e:
        print(f"Error in get_question: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/check_answer', methods=['POST'])
def validate_answer():
    try:
        data = request.json
        response = check_answer(
            data.get('question'),
            data.get('user_answer'),
            data.get('correct_answer'),
            data.get('explanation')
        )
        
        # Ensure response is proper JSON
        if isinstance(response, str):
            try:
                json.loads(response)  # Validate JSON
            except json.JSONDecodeError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid response format"
                }), 500
        
        return jsonify({
            "status": "success",
            "data": response
        })
    except Exception as e:
        print(f"Error in validate_answer: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
