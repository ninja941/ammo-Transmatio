import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_structured_response(
    *,
    model: str,
    reasoning_effort: str,
    system_prompt: str,
    user_content,
    schema_name: str,
    schema
):
    response = client.responses.create(
        model=model,
        reasoning={"effort": reasoning_effort},
        input=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True
            }
        }
    )

    return json.loads(response.output_text)