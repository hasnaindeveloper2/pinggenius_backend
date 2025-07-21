def extract_subject(email_text: str) -> str:
    """
    Extracts the subject line from a cold email.
    Supports both real newlines (\n) and raw /n line separators.

    Args:
        email_text (str): Full email content with possible 'Subject:' line.

    Returns:
        str: Extracted subject line or empty string if not found.
    """
    # Normalize fake "/n" to real newlines
    normalized_text = email_text.replace("/n", "\n")

    for line in normalized_text.splitlines():
        line = line.strip()
        if line.lower().startswith("subject:"):
            return line[len("Subject:"):].strip()
    return ""
