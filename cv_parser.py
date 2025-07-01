import fitz
import re
import os
import ollama
import json


def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def parse_cv_with_ollama(cv_text: str, user_input: str, locations: str) -> dict: # DELETE POSSIBLE GAPS TO HAVE OPTIMISTIC RESULTS MAYBE
    prompt = f"""
You are a CV parsing assistant. Analyse the CV text and extract the following information:
- hard_skills (e.g., Python programming, accounting, ...)
- soft_skills (e.g.,problem-solving, public speaking, ...)
- languages: languages spoken with their proficiency levels (e.g., English - C1, French - B2, ...)
- experience: List of past and present job positions in terms of role title, company, start year - end year, detailed description (e.g., AI Scientist, Sony, 2020-2022, Developed deep learning models for time series forecasting)
- education: education history in terms of degree, institution, starting year - graduation year (e.g., BSc in Computer Science, University of Zurich, 2020-2023)
- keywords: industries, domains or areas of expertise encoded in keywords (e.g., finance, healthcare, AI, ...)
- spurious: additional spurious information in terms of interests, hobbies and more (e.g., horse riding, neuroscience, ...)

- evaluation: write a short paragraph (5-8 sentences, no bullet points) providing an overall candidate's evaluation, that considers BOTH the information from the CV Text and the User Input (the User Input may be empty; if so, rely only on the CV Text for your evaluation):
    - main strengths, stand-out skills, experiences and interests
    - possible gaps or red flags
    - suggested current seniority level (junior/mid/senior)
    - ideal next career step

- job_search_roles: based on all of the above, suggest a list of  2 suitable job titles or keywords to use in a job search (general).
- job_search_locations: use the information in Locations text to suggest suitable locations for job search in terms of city name (e.g., Munich; Bologna).



**Output requirements:**
- Return ONLY a valid JSON object that starts with '{' and ends with '}', with keys: hard_skills, soft_skills, languages, experience, education, keywords, spurious, evaluation, job_search_roles, job_search_locations.
- DO NOT include any explanation, markdown, or text outside the JSON.
- DO NOT use backticks or code blocks.

CV Text:
\"\"\"
{cv_text}
\"\"\"

User Input:
\"\"\"
{user_input}
\"\"\""

Locations:
\"\"\"
{locations}
\"\"\""
"""

    response = ollama.chat(
        model="mistral",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that analyses resumes."},
            {"role": "user", "content": prompt}
        ]
    )
    # Try to extract JSON from model output
    raw = response['message']['content']
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON inside the raw output
        match = re.search(r"{.*}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except Exception:
                data = {"error": "Failed to parse extracted JSON.", "raw_output": raw}
        else:
            data = {"error": "Failed to find JSON in model output.", "raw_output": raw}

    return data


def cv_parser_node(state: dict) -> dict:
    pdf_path = state.get("cv_path", "data/sample_cv.pdf")
    raw_text = extract_text_from_pdf(pdf_path)
    user_input = state.get("user_input", "")
    if not user_input.strip():
        user_input = "No additional information provided by the candidate."
    locations_input = state.get("locations", "Switzerland")
    extracted_data = parse_cv_with_ollama(raw_text, user_input, locations_input)
    print('extracted data keys:', extracted_data.keys())
    print('cv_parser agent has extracted the following data from the CV:', extracted_data)
    # Store new result in state
    state["cv_data"] = extracted_data

    print('cv_parser agent has updated the state, which now has keys:', state.keys())
    
    return state


def get_input_node(state: dict) -> dict:
    # Ask the user for free text input
    user_input = input("Please enter any additional information you'd like the agent to consider:\n> ")

    # Ask the user for preferred locations
    locations = input("Please enter your preferred job locations (comma-separated):\n> ")

    # Store them in the state
    state["user_input"] = user_input.strip()
    state["locations"] = locations.strip()

    print('get_input agent has updated the state, which now has keys:', state.keys())

    return state

