import requests

def get_linkedin_profile_info(query, serp_api_key):
    
    if not query:
        raise ValueError("Query must not be empty")
    
    # get name of the user from the query
    get_name = query
    
    params = {
        "engine": "google",
        "q": f"site:linkedin.com/in/ {query}",
        "api_key": serp_api_key,
        "num": 3
    }

    response = requests.get("https://serpapi.com/search", params=params)
    data = response.json()

    results = []

    for result in data.get("organic_results", []):
        title = result.get("title", "")
        link = result.get("link", "")
        snippet = result.get("snippet", "")

        results.append({
            "name": title.split(" - ")[0],
            "headline": title.split(" - ")[1] if " - " in title else "",
            "linkedin_url": link,
            "about": snippet
        })

    return results

# Example usage
query = "agentic ai developer"  # or a person's name
serp_api_key = "YOUR_SERPAPI_KEY"

profiles = get_linkedin_profile_info(query, serp_api_key)

for p in profiles:
    print(f"Name: {p['name']}")
    print(f"Headline: {p['headline']}")
    print(f"LinkedIn URL: {p['linkedin_url']}")
    print(f"About: {p['about']}")
    print("-" * 50)
