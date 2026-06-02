import json
import re


def repair_json(text: str) -> dict:
    """Best-effort JSON repair. Returns parsed dict or raises."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not repair JSON from: {text[:200]}...")
