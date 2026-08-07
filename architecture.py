from google import genai

API_KEY = "AIzaSy................................"

client = genai.Client(
    api_key=API_KEY
)


def generate_architecture(papers):

    prompt = """
You are an experienced AI researcher.

Read all the research papers.

Generate:

1. Common workflow

2. Generalized architecture

3. Common algorithms

4. Common datasets

5. Evaluation metrics

6. Top 5 research gaps

7. One novel research idea

Represent the workflow like:

Input
↓

Preprocessing
↓

Feature Extraction
↓

Model
↓

Evaluation

Also explain every module.
"""

    for i, paper in enumerate(papers, start=1):

        prompt += f"""

Paper {i}

Title:
{paper['title']}

Abstract:
{paper['abstract']}

"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return response.text