import os, re
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import date

load_dotenv() 
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError(" GEMINI_API_KEY not found in environment variables.")

genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash-lite"

def _build_prompt(upc, weak_topics):
    return f"""
    You are a medical education coach.  

    Topic: "{upc.topic}"
    Historically weak subtopics: {', '.join(weak_topics)}  

    Produce EXACT JSON with this schema (no extra keys):
    {{
    "topic": "str",
    "basics": ["str", ...],
    "focus": ["str", ...],
    "study_path": [
        {{
        "step": 1,
        "modality": "Active Recall",
        "target": "str",
        "deliverable": "str"
        }},
        {{
        "step": 2,
        "modality": "Case-based Learning",
        "target": "str",
        "deliverable": "str"
        }},
        {{
        "step": 3,
        "modality": "MCQ Practice",
        "target": "str",
        "deliverable": "str"
        }},
        {{
        "step": 4,
        "modality": "Review",
        "target": "str",
        "deliverable": "str"
        }}
    ]
    }}
    """.strip()

def generate_study_plan(upc, weak_topics):
    prompt = _build_prompt(upc, weak_topics)
    print("Setting model")
    model = genai.GenerativeModel(MODEL_NAME)
    print("Gemini Model ready")
    response = model.generate_content(prompt)
    text = response.text.strip()

    if not text:
        raise ValueError("Empty response from model.")

    # print("Model response:", text)  # Debugging output

    try:
        json_start = text.index('{')
        json_end = text.rindex('}') + 1
        json_str = text[json_start:json_end]
        import json
        plan = json.loads(json_str)
        return plan
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to parse JSON from model response: {e}\nResponse was: {text}")
    
# Example usage:
# upc = {
#     "topic": "Cardiovascular System",
#     "course": "Human Physiology",
#     "date": "2024-10-15",
#     "hours": 15
# }
# weak_topics = ["Renal Physiology", "Endocrinology"]
# plan = generate_study_plan(upc, weak_topics, date.today())
# print(plan)