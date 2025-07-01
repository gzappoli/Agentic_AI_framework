# job_search_agents.py

import asyncio
from playwright.async_api import async_playwright
from langgraph.graph import StateGraph
from typing import TypedDict
import json
from itertools import product
import random
import csv
import os
import requests


# HELPER FUNCTIONS

# RANDOM MOUSE MOVEMENTS TO OVERCOME BOT DETECTION
async def random_mouse_movements(page):
    # Move mouse in a random pattern
    for _ in range(random.randint(2, 5)):
        x = random.randint(0, 800)
        y = random.randint(0, 600)
        await page.mouse.move(x, y, steps=random.randint(5, 20))
        await page.wait_for_timeout(random.randint(200, 800))


def load_proxies_from_csv(csv_path="data/Free_Proxy_List.csv"):
    proxies = []
    if not os.path.exists(csv_path):
        return proxies
    with open(csv_path, newline='', encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ip = row["ip"].strip('"')
            port = row["port"].strip('"')
            protocol = row["protocols"].strip('"')
            if protocol == "http":
                proxies.append(f"http://{ip}:{port}")
    return proxies

def test_proxy(proxy_url, timeout=5):
    try:
        response = requests.get("https://www.google.com", proxies={"http": proxy_url, "https": proxy_url}, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False

# -----------------------------
# 1. Scraper Logic
# -----------------------------

async def scrape_jobs(role: str, location: str, max_results: int = 2):
    jobs = []
    USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    # Chrome on Android
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    ]

    user_agent = random.choice(USER_AGENTS)
    
    # proxy_list = [None] + load_proxies_from_csv()
    # proxy = random.choice(proxy_list)


    async with async_playwright() as p:
       
        browser = await p.chromium.launch(headless=False, slow_mo=random.randint(300, 500))
        context_args = {"user_agent": user_agent, "locale": "en-US"}
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        await page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})

        await page.goto("https://www.jobs.ch/en/")

        # Accept cookies if popup appears
        try:
            await page.wait_for_selector("button[data-cy='cookie-consent-modal-primary']", timeout=5000)
            await page.click("button[data-cy='cookie-consent-modal-primary']")
            await page.wait_for_timeout(random.randint(300, 1000))
        except Exception as e:
            print("No cookie popup found or failed to accept cookies:", e)
        
        # Human-like behavior
        await random_mouse_movements(page)
        await page.mouse.wheel(0, random.randint(200, 600))
        await page.wait_for_timeout(random.randint(500, 1500))

        await page.fill('#synonym-typeahead-text-field', role)
        await page.wait_for_timeout(random.randint(300, 1000))
        await page.fill('#location-typeahead-text-field', location)
        await page.wait_for_timeout(random.randint(300, 1000))
        await page.keyboard.press("Enter")

        await page.wait_for_timeout(random.randint(4000, 7000))  # Wait for results to load

        detail_page = await context.new_page()

        while len(jobs) < max_results:
            cards = await page.query_selector_all("a[data-cy='job-link']")  

            for card in cards:
                
                title = await card.get_attribute('title')
                location_el = await card.query_selector("xpath=.//div/div[3]/div[1]/p")
                if location_el:
                    location_val = await location_el.inner_text()
                else:
                    location_val = "Unknown"
                company_el = await card.query_selector("xpath=.//div/div[4]/p/strong")
                if company_el:
                    company = await company_el.inner_text()
                else:
                    company = "Unknown"
                link = await card.get_attribute('href')
                link = f"https://www.jobs.ch{link}" if link else ""
                
                # go to link page and extract description text
                await detail_page.goto(link)
                await detail_page.wait_for_timeout(random.randint(2000, 4000))
                # job_page = await browser.new_page()
                # await job_page.goto(link)
                # await job_page.wait_for_timeout(2000)
                desc_el = await detail_page.query_selector("div[data-cy='vacancy-description']") 
                if desc_el:
                    desc = await desc_el.inner_text()
                else:
                    desc = "No description available"
                # await job_page.close()

                jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": location_val.strip(),
                    "description": desc.strip(),
                    "link": link,
                })

                if len(jobs) >= max_results:
                    break

                await asyncio.sleep(random.uniform(1.0, 3.0))

            # Next page
            if len(jobs) < max_results:
                next_btn = await page.query_selector('a[rel="prerender next"]')
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_timeout(4000)
                else:
                    break

        await detail_page.close()
        await browser.close()
        print('jobs', jobs)
        return jobs


# -----------------------------
# 2. LangGraph Nodes
# -----------------------------

async def scrape_jobs_node(state):
    roles = state["cv_data"]["job_search_roles"]
    locations = state["cv_data"]["job_search_locations"]
    all_jobs = []
    seen_links = set()

    for role, location in product(roles, locations):
        print(f"Searching for role: {role} in {location}")
        jobs = await scrape_jobs(role, location)

        for job in jobs:
            if job["link"] not in seen_links:
                seen_links.add(job["link"])
                all_jobs.append(job)

    state["found_jobs"] = all_jobs
    return state


async def save_results_node(state):
    jobs = state["found_jobs"]
    output_dir = r'C:\Users\Giulia\OneDrive\Desktop\Agentic_AI_framework\outputs'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "found_jobs.json")
    with open(output_path, "w") as f:
        json.dump(jobs, f, indent=2)
    print(f"Saved {len(jobs)} jobs to {output_path}")
    return state



