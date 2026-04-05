"""
AI Problem Generator — uses NVIDIA Nemotron model to generate
LeetCode-style coding problems with test cases for the admin dashboard.
"""
import json
import os
import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

ai_bp = Blueprint("ai_helper", __name__)

NVIDIA_API_KEY = os.getenv(
    "NVIDIA_API_KEY",
    "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"
)
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_ID = "nvidia/nemotron-3-super-120b-a12b"


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
  "title": "<Problem Title — inspired by a real LeetCode problem>",
  "description": "<Full problem statement including:\\n- Clear problem description\\n- Input format (what the program reads from stdin)\\n- Output format (what the program prints to stdout)\\n- Constraints\\n- Examples section with explanation\\n- Notes if needed.\\nUse newline characters for formatting.>",
  "sampleTestCases": [
    {"input": "<stdin input>", "output": "<expected stdout>"},
    {"input": "<stdin input>", "output": "<expected stdout>"}
  ],
  "hiddenTestCases": [
    {"input": "<stdin input>", "output": "<expected stdout>"},
    {"input": "<stdin input>", "output": "<expected stdout>"},
    {"input": "<stdin input>", "output": "<expected stdout>"},
    {"input": "<stdin input>", "output": "<expected stdout>"},
    {"input": "<stdin input>", "output": "<expected stdout>"}
  ]
}

RULES:
1. Provide EXACTLY 2 sample test cases and EXACTLY 5 hidden test cases — no more, no less.
2. Every test case must be UNIQUE — no duplicate inputs across sample and hidden cases.
3. Hidden test cases MUST include: a minimal edge case, a boundary/corner case, a medium-sized input, and at least one large input to stress-test solutions.
4. All input/output values MUST be strings representing what a program reads from stdin and prints to stdout.
   - For arrays: "5\\n1 2 3 4 5\\n" (first line = size, second line = elements)
   - For matrices: "3 3\\n1 2 3\\n4 5 6\\n7 8 9\\n" (first line = rows cols)
   - For single values: "42\\n"
   - IMPORTANT: Each input/output MUST end with a newline character \\n
5. The description must be detailed enough for a student to solve without seeing hidden test cases.
6. Ensure ALL test cases have correct, verified outputs consistent with the problem statement.
7. Reply ONLY with the JSON object — no extra text, no markdown fences, no explanation.
8. The problem should be inspired by a real LeetCode problem matching the requested difficulty and topic.
9. If the user mentions a specific LeetCode problem or number, model the problem closely after it.
"""


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

    if not NVIDIA_API_KEY:
        return jsonify({"error": "NVIDIA API key not configured on server."}), 500

    try:
        resp = requests.post(
            NVIDIA_API_URL,
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_ID,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            timeout=120,
        )

        if resp.status_code != 200:
            error_detail = resp.text[:500]
            return jsonify({
                "error": f"NVIDIA API returned {resp.status_code}",
                "detail": error_detail
            }), 502

        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if the model wraps output
        if content.startswith("```"):
            # Remove ```json and trailing ```
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        # Parse and validate JSON
        problem = json.loads(content)

        # Validate required keys
        required = ["title", "description", "sampleTestCases", "hiddenTestCases"]
        for key in required:
            if key not in problem:
                return jsonify({
                    "error": f"AI response missing required field: {key}",
                    "raw": content[:1000]
                }), 502

        return jsonify({
            "success": True,
            "problem": problem
        }), 200

    except json.JSONDecodeError:
        return jsonify({
            "error": "AI returned invalid JSON. Please try again.",
            "raw": content[:1000] if 'content' in dir() else ""
        }), 502
    except requests.exceptions.Timeout:
        return jsonify({"error": "AI request timed out. Please try again."}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Could not connect to NVIDIA API."}), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
