import json
import re


def _safe_eval_math_expr(match):
    expr = match.group(0)
    if re.fullmatch(r"[\d\s\*\+\-\/\.]+", expr):
        try:
            return str(int(eval(expr)))
        except Exception:
            return "0"
    return "0"


def _recover_failed_generation(error_msg: str) -> dict | None:
    match = re.search(r"'failed_generation':\s*'(.*?)'}}", error_msg, re.DOTALL)
    if not match:
        return None

    raw_json = match.group(1)
    # The original replace
    raw_json = raw_json.replace("\\n", "\n").replace('\\"', '"')

    # We should also replace \' with ' since it breaks json.loads
    # Let's test if we add:
    raw_json = raw_json.replace("\\'", "'")

    fixed_json = re.sub(
        r"[\d\.]+(?:\s*[\*\+\-\/]\s*[\d\.]+)+",
        _safe_eval_math_expr,
        raw_json,
    )

    try:
        data = json.loads(fixed_json)
        return {k: int(float(v)) if isinstance(v, int | float) else v for k, v in data.items()}
    except Exception as e:
        print("ERROR PARSING JSON:", e)
        return None


error_msg = """Error code: 400 - {'error': {'message': "Failed to generate JSON", 'type': 'invalid_request_error', 'code': 'json_validate_failed', 'failed_generation': '{\\n  "reasoning": "we\\'ll do this",\\n   "is_valid": true,\\n   "rejection_reason": "",\\n   "car_km": 0,\\n   "two_wheeler_km": 2.5 * 365\\n}'}}"""

print(_recover_failed_generation(error_msg))
