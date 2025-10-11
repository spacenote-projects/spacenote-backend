def parse_line_based_response(content: str) -> dict[str, str]:
    """Parse line-based response format into dict."""
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
