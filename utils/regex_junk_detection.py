import re

SPAM_KEYWORDS = [
    r"congratulations", r"lottery", r"you won", r"winner",
    r"free money", r"claim now", r"urgent action",
    r"100% free", r"credit score", r"work from home",
    r"click here", r"limited offer", r"prince",
]

BAD_DOMAINS = [
    "cheapoffers.com", "randommail.ru", "tempmail", "nigerian-prince",
]

def is_junk_email(input_text: str) -> bool:
    # Extract fields
    subject_match = re.search(r"Subject:\s*(.*)", input_text)
    from_match = re.search(r"From:\s*(.*)", input_text)
    body_match = re.search(r"Body:\s*(.*)", input_text, re.DOTALL)

    subject = subject_match.group(1).strip() if subject_match else ""
    sender = from_match.group(1).strip() if from_match else ""
    body = body_match.group(1).strip() if body_match else ""

    text = f"{subject} {body}".lower()

    # Keyword-based detection
    for kw in SPAM_KEYWORDS:
        if re.search(kw, text):
            return True

    # Suspicious sender domains
    sender = sender.lower()
    if any(domain in sender for domain in BAD_DOMAINS):
        return True

    # Too many links
    if text.count("http") > 3:
        return True

    # ALL CAPS subject
    if subject.isupper() and len(subject.split()) > 3:
        return True

    return False

