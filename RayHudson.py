import requests, json

def generate_match_preview(prediction: dict) -> str:
    prompt = f"""
You are a football analyst. Given these match prediction stats, write a 3-sentence preview.
Respond ONLY with plain text, no markdown.

Data: {json.dumps(prediction)}
"""
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    })
    return response.json()["response"]
    