import re

def extract_name(email: str) -> str:
    match = re.search(r"[\w\.-]+@([\w\.-]+)", email)
    if match:
        return match.group(1).split('.')[0].capitalize()  # e.g. codewithhasnain → Codewithhasnain
    return "there"
