"""
AI Problem Generator — uses NVIDIA Nemotron-3-Super-120b-a12b model
to generate LeetCode-style coding problems for the admin dashboard.
Uses requests library (no additional dependencies needed).
"""
import json
import os
import re
import requests as req
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

ai_bp = Blueprint("ai_helper", __name__)

# ── NVIDIA Config ──────────────────────────────────────────────
# Reads from Railway environment variable NVIDIA_API_KEY
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "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")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Primary model — Nemotron-3-Super as requested by user
PRIMARY_MODEL = "nvidia/nemotron-3-super-120b-a12b"

# Fallback models in case primary is unavailable
FALLBACK_MODELS = [
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-70b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
]


def _require_master():
    claims = get_jwt()
    if claims.get("role") != "master":
        return jsonify({"error": "Admin access required"}), 403
    return None


SYSTEM_PROMPT = """You are a competitive-programming problem designer who specializes in LeetCode-style problems.

When the user asks for a coding problem (e.g. "I need a medium level matrix problem"), you MUST:
1. Pick a real LeetCode problem matching the requested difficulty and topic.
2. Create a problem INSPIRED BY it (adapt it, don't copy verbatim).
3. Return ONLY a valid JSON object — no extra text before or after.

The JSON must have exactly these keys:
{
  "title": "<Problem Title>",
  "description": "<Full problem statement with: description, Input format, Output format, Constraints, Examples with explanation>",
  "sampleTestCases": [
    {"input": "<stdin string ending with newline>", "output": "<stdout string ending with newline>"},
    {"input": "<stdin string ending with newline>", "output": "<stdout string ending with newline>"}
  ],
  "hiddenTestCases": [
    {"input": "<stdin>", "output": "<stdout>"},
    {"input": "<stdin>", "output": "<stdout>"},
    {"input": "<stdin>", "output": "<stdout>"},
    {"input": "<stdin>", "output": "<stdout>"},
    {"input": "<stdin>", "output": "<stdout>"}
  ]
}

RULES:
1. EXACTLY 2 sample test cases and EXACTLY 5 hidden test cases.
2. All test cases must be UNIQUE — no duplicate inputs.
3. Hidden cases must include: empty/edge case, boundary case, medium input, large stress input.
4. Input/output are stdin/stdout strings. Example for array of 5: "5\\n1 2 3 4 5\\n"
5. Every input and output string MUST end with \\n
6. Outputs must be mathematically correct.
7. Reply ONLY with the JSON — absolutely no markdown fences, no explanation text.
"""


def _extract_json(content):
    """Extract and parse JSON from model response, handling markdown fences."""
    content = content.strip()

    # Remove markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        lines = lines[1:]  # remove ```json or ```
        while lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    # Try direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to extract just the JSON object using regex
    match = re.search(r'\{[\s\S]*\}', content)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Cannot extract valid JSON from response: {content[:200]}")


def _call_model(model_id, user_prompt):
    """Call NVIDIA API with given model using requests."""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    resp = req.post(NVIDIA_BASE_URL, headers=headers, json=payload, timeout=120)

    if resp.status_code == 401 or resp.status_code == 403:
        raise PermissionError(f"NVIDIA API auth failed ({resp.status_code}): {resp.text[:200]}")

    if resp.status_code != 200:
        raise RuntimeError(f"NVIDIA API error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


@ai_bp.route("/generate-problem", methods=["POST"])
@jwt_required()
def generate_problem():
    """Generate a coding problem using NVIDIA Nemotron model."""
    err = _require_master()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    user_prompt = body.get("prompt", "").strip()
    if not user_prompt:
        return jsonify({"error": "Please describe what kind of problem you want."}), 400

    if not NVIDIA_API_KEY or not NVIDIA_API_KEY.startswith("nvapi-"):
        return jsonify({"error": "Invalid NVIDIA API key. Must start with nvapi-. Set NVIDIA_API_KEY in Railway variables."}), 500

    # Try primary model first, then fallbacks
    models_to_try = [PRIMARY_MODEL] + FALLBACK_MODELS
    last_error = None

    for model_id in models_to_try:
        try:
            raw_content = _call_model(model_id, user_prompt)
            problem = _extract_json(raw_content)

            # Validate required keys
            required = ["title", "description", "sampleTestCases", "hiddenTestCases"]
            missing = [k for k in required if k not in problem]
            if missing:
                last_error = f"Model {model_id} response missing fields: {missing}"
                continue

            return jsonify({
                "success": True,
                "problem": problem,
                "model_used": model_id
            }), 200

        except PermissionError as e:
            # Auth error — no point trying other models with same key
            return jsonify({
                "error": f"NVIDIA API authentication failed. Please update NVIDIA_API_KEY in Railway variables.",
                "detail": str(e)[:200]
            }), 502

        except (ValueError, json.JSONDecodeError) as e:
            last_error = f"Model {model_id} returned invalid JSON: {str(e)}"
            continue

        except req.exceptions.Timeout:
            last_error = f"Model {model_id} timed out"
            continue

        except Exception as e:
            last_error = f"Model {model_id}: {str(e)[:200]}"
            continue

    return jsonify({
        "error": f"Failed to generate problem. Error: {last_error}",
    }), 502


@ai_bp.route("/test-key", methods=["GET"])
@jwt_required()
def test_key():
    """Debug endpoint — test if NVIDIA API key works."""
    err = _require_master()
    if err:
        return err

    key_preview = (NVIDIA_API_KEY[:16] + "...") if NVIDIA_API_KEY else "NOT SET"

    try:
        content = _call_model(PRIMARY_MODEL, "Reply with just the word: WORKING")
        return jsonify({
            "success": True,
            "model": PRIMARY_MODEL,
            "response": content[:100],
            "key_preview": key_preview
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)[:300],
            "key_preview": key_preview,
            "key_valid_format": NVIDIA_API_KEY.startswith("nvapi-") if NVIDIA_API_KEY else False
        }), 502
