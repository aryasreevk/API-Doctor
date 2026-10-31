
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.5-flash-lite"

SUPPORTED_LANGUAGES = [
    "Python",
    "C",
    "C++",
    "Java",
    "JavaScript",
    "TypeScript",
    "PHP",
    "HTML",
    "SQL",
    "Go"
]


async def generate_code_fix(analysis, language):

    if not API_KEY:
        raise ValueError("Gemini API key is missing")

    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported programming language")

    prompt = f"""
You are an experienced software engineer
and API debugging specialist.

Analyse the following API diagnostic results:

HTTP Status Code: {analysis.get('status_code')}
Response Time: {analysis.get('response_time_ms')} ms
JSON Valid: {analysis.get('json_valid')}
Detected Issues: {analysis.get('issues')}
Suggestions: {analysis.get('suggestions')}

The user selected this language: {language}

Your task is to generate a useful and practical code fix.

IMPORTANT RULES:

1. FRAMEWORK INDEPENDENCE
- Generate framework-independent code by default.
- Do not assume Flask, Django, FastAPI, Express,
  Spring Boot or any other framework.
- Use standard language features or commonly
  available libraries where appropriate.
- Do not invent project structure or API details.

2. FRAMEWORK ASSUMPTIONS
- If framework information is unavailable,
  clearly state that the example is framework-independent.
- Do not generate framework-specific code unless
  the framework is explicitly known.
- Clearly mention any required dependencies.

3. CLIENT AND SERVER SIDE
- Distinguish between client-side and server-side issues.
- If the issue concerns API usage, provide a suitable
  client-side example where possible.
- If the issue requires changes to the API server,
  explain what the server developer should correct.
- Do not assume the user owns or controls the API.

4. LANGUAGE REQUIREMENTS
- Generate valid and readable {language} code.
- For HTML, generate appropriate markup and explain
  any required JavaScript integration.
- For SQL, provide suitable queries and state
  assumptions about the database schema.
- Include appropriate error handling where applicable.

5. ACCURACY
- Use only the information provided.
- Distinguish confirmed issues from possible causes.
- Never invent unavailable API details.
- Clearly state assumptions.
- Do not claim that generated code has been tested.

6. RESPONSE FORMAT

Provide the following sections:

1. Problem Explanation
2. Possible Cause
3. Recommended Solution
4. Corrected Example Code
5. Explanation of the Correction

If the API is already healthy:
- State that no major correction is required.
- Provide useful optional improvements only.
- Do not invent a problem.

Keep the response concise and practical.
"""

    client = genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(timeout=60000)
    )

    async with client.aio as ai_client:

        response = await ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1200
            )
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response"
            )

        return response.text
