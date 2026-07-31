import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Your OpenRouter API key
API_KEY = os.getenv("OPENROUTER_API_KEY")

# Send a message to the AI
response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "cohere/north-mini-code:free",
        "messages": [
            {
                "role": "user",
                "content": "Say hello and tell me you are connected!"
            }
        ]
    }
)

# Print the reply
result = response.json()
print(result["choices"][0]["message"]["content"])