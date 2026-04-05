"""
AI Problem Generator — uses NVIDIA Nemotron-3-Super-120b-a12b model
to generate LeetCode-style coding problems for the admin dashboard.

Uses the OpenAI-compatible SDK as recommended by NVIDIA.
"""
import json
import os
import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

ai_bp = Blueprint("ai_helper", __name__)

# ── NVIDIA Config ──────────────────────────────────────────────
# IMPORTANT: Set NVIDIA_API_KEY in Railway environment variables
# Get your key from: https://build.nvidia.com → Profile → API Keys
NVIDIA_API_KEY = os.getenv("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", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Primary model — Nemotron-3-Super as requested
PRIMARY_MODEL = "nvidia/nemotron-3-super-120b-a12b"

# Fallback models in case primary is unavailable (tried in order)
FALLBACK_MODELS = [
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-70b-instruct",
]


def _require_master():
    claims = get_jwt()
    if claims.get("role") != "master":
        return jsonify({"error": "Admin access required"}), 403
    return None


SYSTEM_PROMPT = """You are a competitive-programming problem designer who specializes in LeetCode-style problems.

When the user asks for a coding problem (e.g. "I need a medium level matrix problem"), you MUST:
1. Search your knowledge of real LeetCode problems matching the requested difficulty and topic/category.
2. Create a problem INSPIRED BY a real LeetCode problem (adapt it, don't copy verbatim).
3. Include the problem name, a detailed description, and test cases.

Your response MUST be a valid JSON object with exactly these keys:
{
  "title": "<Problem Title>",
  "description": "<Full problem statement with input/output format, constraints, and examples>",
  "sampleTestCases": [
    {"input": "<stdin input string>", "output": "<expected stdout string>"},
    {"input": "<stdin input string>", "output": "<expected stdout string>"}
  ],
  "hiddenTestCases": [
    {"input": "<stdin input string>", "output": "<expected stdout string>"},
    {"input": "<stdin input string>", "output": "<expected stdout string>"},
    {"input": "<stdin input string>", "output": "<expected stdout string>"},
    {"input": "<stdin input string>", "output": "<expected stdout string>"},
    {"input": "<stdin input string>", "output": "<expected stdout string>"}
  ]
}

STRICT RULES:
1. Provide EXACTLY 2 sample test cases and EXACTLY 5 hidden test cases.
2. Every test case must be UNIQUE — no duplicate inputs.
3. Hidden test cases must include: edge case, boundary case, medium input, large stress-test input.
4. Input/output must be stdin/stdout strings — e.g. "5\\n1 2 3 4 5\\n" for an array of 5 elements.
5. Each input and output string MUST end with a newline \\n character.
6. All test case outputs must be mathematically verified and correct.
7. Reply ONLY with the raw JSON object — no markdown fences, no explanation text.
"""


def _call_nvidia(model_id, user_prompt):
    """Call NVIDIA API using the OpenAI-compatible SDK."""
    from openai import OpenAI

    client = OpenAI(
        base_url=NVIDIA_BASE_URL,
        api_key=NVIDIA_API_KEY,
    )

    completion = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=4096,
        timeout=120,
    )
    return completion.choices[0].message.content.strip()


def _extract_json(content):
    """Extract JSON from model response, handling markdown fences."""
    # Strip markdown fences if present
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last ``` if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    # Try direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON object using regex
    match = re.search(r'\{[\s\S]*\}', content)
    if match:
        return json.loads(match.group())

    raise json.JSONDecodeError("No valid JSON found", content, 0)


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
        return jsonify({"error": "Invalid NVIDIA API key. Must start with nvapi-"}), 500

    # Try primary model first, then fallbacks
    models_to_try = [PRIMARY_MODEL] + FALLBACK_MODELS
    last_error = None

    for model_id in models_to_try:
        try:
            content = _call_nvidia(model_id, user_prompt)
            problem = _extract_json(content)

            # Validate required keys
            required = ["title", "description", "sampleTestCases", "hiddenTestCases"]
            missing = [k for k in required if k not in problem]
            if missing:
                last_error = f"AI response missing fields: {missing}"
                continue

            return jsonify({
                "success": True,
                "problem": problem,
                "model_used": model_id
            }), 200

        except json.JSONDecodeError as e:
            last_error = f"Model {model_id} returned invalid JSON: {str(e)}"
            continue
        except Exception as e:
            err_str = str(e)
            last_error = f"Model {model_id} error: {err_str}"
            # If it's a 403 auth error, don't try fallbacks with different model
            if "403" in err_str or "401" in err_str:
                return jsonify({
                    "error": "NVIDIA API authentication failed (403). Please check your API key in Railway variables.",
                    "detail": err_str[:300]
                }), 502
            continue

    return jsonify({
        "error": f"All models failed. Last error: {last_error}",
    }), 502


@ai_bp.route("/test-key", methods=["GET"])
@jwt_required()
def test_key():
    """Test endpoint to verify NVIDIA API key is working."""
    err = _require_master()
    if err:
        return err

    try:
        from openai import OpenAI
        client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)
        result = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[{"role": "user", "content": "Reply with just: OK"}],
            max_tokens=5,
            timeout=30,
        )
        return jsonify({
            "success": True,
            "model": PRIMARY_MODEL,
            "response": result.choices[0].message.content,
            "key_prefix": NVIDIA_API_KEY[:12] + "..."
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "key_prefix": NVIDIA_API_KEY[:12] + "..." if NVIDIA_API_KEY else "NOT SET"
        }), 502
