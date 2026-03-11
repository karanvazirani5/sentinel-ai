import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_outreach_email(company_name, contact_name, industry):
    prompt = f"""
Write a short professional cold outreach email.

Target:
Company: {company_name}
Contact: {contact_name}
Industry: {industry}

Goal:
Introduce an AI automation platform that helps companies automate outbound sales workflows.

Keep it under 120 words.
Friendly but professional.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You write high-performing sales emails."},
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content
