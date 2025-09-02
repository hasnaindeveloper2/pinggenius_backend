import re
from agents import Runner
from utils.followups_agent import followups_generator_agent


def smart_split_variations(output: str) -> list[str]:
    # Step 1: Split on "---" blocks
    parts = re.split(r"\n\s*---\s*\n", output.strip())

    cleaned = []
    for part in parts:
        # Step 2: Remove "Email 1", "Email 2", etc.
        part = re.sub(
            r"^(Email|Follow[\-\s]*up)\s*\d+\s*", "", part.strip(), flags=re.IGNORECASE
        )

        # Step 3: Remove leftover '---' if any
        part = part.replace("---", "").strip()
        
        # Step 4: remove any labels e.g. email 1 or followup 2
        part = part.replace("Email 1", "").strip()

        # Step 4: Only keep non-empty
        if part:
            cleaned.append(part)

    return cleaned


async def generate_followups(contact, base_email: str, num):
    """
    Generate follow-up emails using existing followups_generator_agent
    """
    input_prompt = f"""
Contact Info:
Name: {contact.get('name')}
Role: {contact.get('role')}
Company Website: {contact.get('website', 'Not provided')}
LinkedIn: {contact.get('linkedin_url')}

We already sent them this first outreach:
---
{base_email}
---

Now generate {num} polite follow-up emails that:
- Reference the first outreach briefly
- Stay in the same tone
- Are short, relevant, and focused on getting a reply
- Each follow-up should be unique and not just a rephrase
- End with a warm, best or best regard {contact.get('name')}

Important: 
Format them like:

---
Email 1

---
Email 2
"""

    result = await Runner.run(followups_generator_agent, input=input_prompt)
    return smart_split_variations(result.final_output)
