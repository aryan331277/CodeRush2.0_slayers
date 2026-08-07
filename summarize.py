from google import genai

# Paste your Gemini API key here
API_KEY = "YOUR_GEMINI_API_KEY"

client = genai.Client(api_key=API_KEY)


def summarize_papers(papers):

    prompt = """
You are an expert AI research assistant.

You will receive multiple research papers.

For EACH paper provide:

1. Short Summary
2. Main Contribution
3. Key Findings
4. Applications

Finally provide:

• Overall comparison

• Research gaps

• Possible new research ideas
"""

    for i, paper in enumerate(papers, start=1):

        prompt += f"""

Paper {i}

Title:
{paper['title']}

Year:
{paper['year']}

Source:
{paper['source']}

Abstract:
{paper['abstract']}

"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return response.text