from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from config import Config
import urllib.request
import urllib.error
import json
import os

complexity_bp = Blueprint("complexity", __name__)

# Supported HuggingFace models for code analysis
SUPPORTED_MODELS = {
    "Qwen/Qwen2.5-Coder-7B-Instruct",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "meta-llama/Llama-3.1-8B-Instruct",
    "microsoft/Phi-3.5-mini-instruct",
}

ANALYSIS_PROMPT = """You are an expert algorithm and data structures analyst. Analyze the given code and respond ONLY with a valid JSON object. No markdown, no backticks, no explanation outside the JSON.

JSON structure to follow exactly:
{{
  "time_complexity": "Big-O notation e.g. O(n^2)",
  "space_complexity": "Big-O notation e.g. O(n)",
  "algorithm": ["main algorithm name", "technique used"],
  "explanation": "1-2 sentence explanation of why this complexity",
  "optimization": "A concrete suggestion to improve complexity, or null if already optimal"
}}

Code to analyze:
```
{code}
```"""


@complexity_bp.route("/analyze", methods=["POST"])
@jwt_required()
def analyze_complexity():
    """
    Analyze the time & space complexity of submitted code using a HuggingFace LLM.
    Uses the server-configured HF token by default. Students can optionally
    provide their own token to override.
    """
    data = request.get_json()
    code = (data.get("code") or "").strip()
    hf_token = (data.get("hfToken") or "").strip()
    model = (data.get("model") or "Qwen/Qwen2.5-Coder-7B-Instruct").strip()

    if not code:
        return jsonify({"error": "No code provided"}), 400

    # Use server-side token if the user didn't provide one
    if not hf_token:
        hf_token = Config.HF_API_TOKEN

    if not hf_token:
        return jsonify({"error": "No HuggingFace API token configured. Please contact your administrator or enter your own token."}), 400

    if model not in SUPPORTED_MODELS:
        return jsonify({"error": f"Unsupported model. Choose one of: {', '.join(SUPPORTED_MODELS)}"}), 400

    prompt = ANALYSIS_PROMPT.format(code=code)

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
        "temperature": 0.1,
        "stream": False,
    }).encode("utf-8")

    api_url = "https://router.huggingface.co/v1/chat/completions"

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            err_data = json.loads(body)
            msg = err_data.get("error", {})
            if isinstance(msg, dict):
                msg = msg.get("message", body)
        except Exception:
            msg = body
        return jsonify({"error": f"HuggingFace API error: {msg}"}), e.code
    except urllib.error.URLError as e:
        return jsonify({"error": f"Network error reaching HuggingFace: {str(e.reason)}"}), 503
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    try:
        hf_response = json.loads(raw)
        content = hf_response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return jsonify({"error": "Unexpected response format from HuggingFace", "raw": raw[:500]}), 502

    # Try to parse embedded JSON from the model's text response
    parsed = None
    # Find the first {...} block in the response
    start = content.find("{")
    end = content.rfind("}") + 1
    if start != -1 and end > start:
        try:
            parsed = json.loads(content[start:end])
        except json.JSONDecodeError:
            pass

    if parsed:
        return jsonify({
            "success": True,
            "time_complexity": parsed.get("time_complexity", "N/A"),
            "space_complexity": parsed.get("space_complexity", "N/A"),
            "algorithm": parsed.get("algorithm", []),
            "explanation": parsed.get("explanation", ""),
            "optimization": parsed.get("optimization"),
        }), 200
    else:
        # Return raw text if JSON parsing fails
        return jsonify({
            "success": True,
            "raw": content,
        }), 200


@complexity_bp.route("/status", methods=["GET"])
@jwt_required()
def token_status():
    """Check if the server has a HuggingFace token configured."""
    has_token = bool(Config.HF_API_TOKEN)
    return jsonify({"serverTokenAvailable": has_token}), 200
