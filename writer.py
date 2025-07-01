import asyncio
from langgraph.graph import StateGraph
from typing import TypedDict
import json
from itertools import product
import random
import csv
import os
import requests
import pandas as pd



def calculate_final_score(subscores: dict) -> float:
    weights = {
        "hard_skills_score": 0.35,
        "soft_skills_score": 0.05,
        "language_score": 0.15,
        "experience_score": 0.35,
        "education_score": 0.10,
    }
    final_score = sum(subscores[key] * weight for key, weight in weights.items())
    return round(final_score, 2)

async def write_csv_node(state):
    jobs = state["found_jobs"]
    matches = state["match_results"]
    new_rows = []

    output_dir = r'C:\Users\Giulia\OneDrive\Desktop\Agentic_AI_framework\outputs'
    output_file = os.path.join(output_dir, "job_matches.csv")
    columns = ["job_title", "company", "location", "description", "hard_skills_score", "soft_skills_score", "language_score", "experience_score", "education_score", "interest_score", "match_evaluation", "tot_weighted_score (interests not included)"]

    if os.path.exists(output_file):
        df = pd.read_csv(output_file)
    else:
        df = pd.DataFrame(columns=columns)
    
    for job, match in zip(jobs, matches):
        tot_score = calculate_final_score(match)
        new_rows.append({
            "job_title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "description": job.get("description", ""),
            "hard_skills_score": match.get("hard_skills_score", -1),
            "soft_skills_score": match.get("soft_skills_score", -1),
            "language_score": match.get("language_score", -1),
            "experience_score": match.get("experience_score", -1),
            "education_score": match.get("education_score", -1),
            "interest_score": match.get("interest_score", -1),
            "match_evaluation": match.get("match_evaluation", ""),
            "tot_score": tot_score
        })
    
    new_df = pd.DataFrame(new_rows, columns=columns)
    df = pd.concat([new_df, df], ignore_index=True)
    
    # Save the dataframe to a CSV file
    df.to_csv(output_file, index=False)
    
    state["match_csv"] = df
    
    return state

