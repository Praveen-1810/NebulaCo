import requests
from nebula.logger import get_logger

logger = get_logger("LLMBridge")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2:1.5b"


def process_with_llm(payload: dict) -> dict:

    try:
        if payload["task"] == "summarize_screen":

            prompt = (
                "Summarize this screen text in simple words "
                "in 4 short lines:\n\n"
                f"{payload['content'][:800]}"
            )

        elif payload["task"] == "screen_qa":

            prompt = (
                f"Based only on this screen text:\n\n"
                f"{payload['content'][:800]}\n\n"
                f"Answer this question:\n{payload['question']}"
            )

        else:
            return {"response": ""}

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 120,
                    "temperature": 0.2
                }
            },
            timeout=120
        )

        result = response.json()

        return {"response": result.get("response", "").strip()}

    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return {"response": ""}
