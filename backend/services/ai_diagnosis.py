
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.5-flash-lite"


async def generate_ai_diagnosis(analysis):

    if not API_KEY:
        raise ValueError("Gemini API key is missing")

    prompt = f"""
    You are an API debugging assistant.

    Analyze these diagnostic results:

    HTTP Status: {analysis.get('status_code')}
    Response Time: {analysis.get('response_time_ms')} ms
    JSON Valid: {analysis.get('json_valid')}
    Issues: {analysis.get('issues')}
    Suggestions: {analysis.get('suggestions')}

    Give a concise report with:

    1. Problem explanation
    2. Possible causes
    3. Recommended fixes

    Distinguish confirmed facts from possible causes.
    Do not invent information.
    Keep the answer under 200 words.
    """

    client = genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(timeout=60000)
    )

    try:
        async with client.aio as ai_client:

            response = await ai_client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=500
                )
            )

            if not response.text:
                raise RuntimeError("Empty Gemini response")

            return response.text

    finally:
        await client.aio.aclose()
