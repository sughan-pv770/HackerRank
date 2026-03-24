"""Test which HuggingFace models are currently available."""
import urllib.request
import urllib.error
import json

HF_TOKEN = "your_huggingface_token_here"

MODELS = [
    "Qwen/Qwen2.5-Coder-7B-Instruct",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "meta-llama/Llama-3.1-8B-Instruct",
    "microsoft/Phi-3.5-mini-instruct",
    "Qwen/Qwen2.5-Coder-32B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFaceH4/zephyr-7b-beta",
    "google/gemma-2-2b-it",
    "microsoft/Phi-3-mini-4k-instruct",
]

for model in MODELS:
    api_url = "https://router.huggingface.co/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Say hello in one word."}],
        "max_tokens": 10,
        "temperature": 0.1,
        "stream": False,
    }).encode()
    req = urllib.request.Request(api_url, data=payload, headers={
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            content = data["choices"][0]["message"]["content"]
            print(f"  [OK]   {model} -> '{content[:50]}'")
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        print(f"  [FAIL] {model} -> HTTP {e.code}: {body[:120]}")
    except Exception as e:
        print(f"  [FAIL] {model} -> {e}")
