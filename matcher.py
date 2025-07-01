import fitz
import re
import os
import ollama
import json





def match_with_ollama(cv_data: dict, job: dict) -> dict: 
    cv_json = json.dumps(cv_data, indent=2)
    jobs_json = json.dumps(job, indent=2)
    prompt = f"""
You are an expert in matching candidates with job descriptions.  
Your task is to analyze the job advertisement below and the candidate’s CV, then provide a detailed match analysis.

**Instructions:**
- Provide separate scores (0–100) for each of these criteria:
    - hard_skills_score: hard skills requested by the job vs. hard skills of the candidate
    - soft_skills_score: soft skills requested by the job vs. soft skills of the candidate
    - language_score: languages requested by the job vs. languages of the candidate
    - experience_score: experience requested by the job vs. experience of the candidate
    - education_score: academic degrees and fields requested by the job vs. education of the candidate
    - interest_score: alignment of the job topic with the candidate's interests

- Write an **evaluation** of 5–8 sentences that **explicitly highlights**:
  - The **specific skills, languages, experience, or education that are a good fit** — mention them by name.
  - The **specific gaps or mismatches** — mention exactly what is missing or weaker.
  - Use clear phrases like: *“The position requires X but the candidate has Y”*, *“The job needs X, which the candidate fully meets”*, etc.
  - Be direct, factual, and concise.
**Do NOT** calculate a total score — only provide the subscores and the evaluation.


**Output requirements:** 
- Return ONLY a valid JSON object that starts with '{' and ends with '}', with keys: hard_skills_score, soft_skills_score, language_score, experience_score, education_score, interest_score, match_evaluation.
- DO NOT include any explanation, text, markdown, or code blocks outside the JSON.

**Candidate's CV data:**
\"\"\"
{cv_json}
\"\"\"

**Job description:**
\"\"\"
{jobs_json}
\"\"\"

**Output example:**
{{
  "hard_skills_score": 80,
  "soft_skills_score": 70,
  "languages_score": 50,
  "experience_score": 85,
  "education_score": 90,
  "interests_score": 80,
  "evaluation": "The job requires MATLAB experience, but the candidate only lists Python and R. However, the candidate has extensive experience with PyTorch, which is explicitly required for the role. The position needs a German-speaking candidate, but the CV shows only English proficiency. The candidate’s years of relevant experience exceed the job’s minimum requirements. Their educational background fully aligns with the job’s expectations. Soft skills match well, but the candidate could improve in teamwork skills if the job emphasizes collaboration. Overall, the candidate has strong technical alignment but a language gap that may need to be addressed."
}}

"""

    response = ollama.chat(
        model="mistral",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that analyses texts."},
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


def match_node(state: dict) -> dict:
    cv_data = state['cv_data']
    found_jobs = state['found_jobs']
    match_results = []
    for job in found_jobs:
        match_result = match_with_ollama(cv_data, found_jobs)
        match_results.append(match_result)
    state['match_results'] = match_results
    return state


