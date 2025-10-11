def parse_line_based_response(content: str) -> dict[str, str]:
    """
    Parse line-based response format into dict.

    We use a simple line-based format (key: value) instead of JSON for LLM responses
    because it's more resilient to LLM errors:

    - JSON parsing fails completely on any syntax error (missing quotes, commas, etc.)
    - Line-based parsing can skip malformed lines and recover
    - LLMs frequently produce invalid JSON, especially in streaming contexts
    - This format provides graceful degradation instead of complete failure

    Format:
        operation_type: create_note
        space_slug: tasks
        title: Buy milk

    Invalid lines are silently skipped, allowing partial parsing on errors.
    """
    parsed_data: dict[str, str] = {}
    for raw_line in content.strip().split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        parsed_data[key.strip()] = value.strip()
    return parsed_data
