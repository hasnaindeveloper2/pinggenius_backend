import re


def extract_name(sender: str) -> str:
    # e.g. "Hasnain <hasnain@example.com>" → "Hasnain"
    match = re.match(r"^(.*?)(?:\s*<.*>)?$", sender.strip())
    name = match.group(1).strip().replace('"', "") if match else "there"
    return name or "there"