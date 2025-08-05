import os
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


def fetch_linkedin_data(linkedin_url: str):
    if not linkedin_url or "linkedin.com" not in linkedin_url:
        return {"error": "Invalid LinkedIn URL"}

    profile_id = linkedin_url.split("/")[-2]  # crude but works
    query = f"{profile_id} site:linkedin.com/in/"

    search = GoogleSearch({"q": query, "engine": "google", "api_key": SERPAPI_API_KEY})

    results = search.get_dict()
    if "error" in results:
        return {"error": results["error"]}

    organic = results.get("organic_results", [])
    if not organic:
        return {"error": "No profile found"}

    snippet = organic[0].get("snippet", "")
    title = organic[0].get("title", "")
    link = organic[0].get("link", "")

    return {
        "name": title.split(" - ")[0] if "-" in title else title,
        "headline": title.split(" - ")[1] if "-" in title else "",
        "about": snippet,
        "profile_link": link,
    }


def guardrail_linkedin_scrape(url: str):
    data = fetch_linkedin_data(url)

    if "error" in data:
        return {"status": "fail", "message": data["error"]}

    if len(data.get("about", "")) < 20:
        return {"status": "fail", "message": "Too little info from SERP"}

    print(data)
    return {"status": "success", "data": data}


guardrail_linkedin_scrape("https://www.linkedin.com/in/hasnainxdev/")
