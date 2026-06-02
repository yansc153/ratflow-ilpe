def truncate(text: str, max_len: int = 1900) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def strip_markdown_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text
