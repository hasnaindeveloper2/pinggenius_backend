from agents import Runner
from utils.email_generator import generator_agent, config, smart_split_variations


async def generate_followups(contact, base_email: str, num):
    """
    Generate follow-up emails using existing generator_agent
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
- End with a professional closing

Important: 
Format them like:

---
Follow-up 1

---
Follow-up 2
"""

    result = await Runner.run(generator_agent, run_config=config, input=input_prompt)
    return smart_split_variations(result.final_output)
