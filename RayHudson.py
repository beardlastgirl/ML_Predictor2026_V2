import requests, json
import logging

def generate_prompt(prediction: dict) -> str:
    return f"""
You are a football analyst. Given these match prediction stats, write a 3-sentence preview.
Respond ONLY with plain text, no markdown.

Data: {json.dumps(prediction)}
"""

def send_request(prompt: str) -> requests.Response | None:
    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "qwen2.5:7b",
            "prompt": prompt,
            "max_tokens": 100,
            "temperature": 0.7
        })
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending request: {e}")
        return None

def generate_match_preview(prediction: dict) -> str:
    prompt = generate_prompt(prediction)
    response = send_request(prompt)
    if response is None:
        return "Error generating match preview"
    return response.text