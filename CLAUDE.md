# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**PROTOTYPE MODE** - This project is in active prototype development. Breaking changes are acceptable and expected. Do not maintain backward compatibility when making improvements.

## Critical Guidelines

1. **Always communicate in English** - Regardless of the language the user speaks, always respond in English. All code, comments, and documentation must be in English.

2. **Minimal documentation** - Only add comments/documentation when it simplifies understanding and isn't obvious from the code itself. Keep it strictly relevant and concise.

3. **Critical thinking** - Always critically evaluate user ideas. Users can make mistakes. Think first about whether the user's idea is good before implementing.

## Development Commands

- `just agent-start` - Start the application on port 3101
- `just agent-stop` - Stop the application
- `just dev` - Never run this command. It's for humans only.
- `just lint` - Run linters after making code changes

## API Testing

- **Use Python with requests library** for testing API endpoints instead of curl
- Claude Code has execution restrictions - only certain commands can run without user approval
- While `curl` is partially allowed, complex curl commands (with POST data, headers, etc.) require approval each time
- Python is fully allowed, making it better for API testing without interrupting the user
- Example: `python3 -c "import requests; r = requests.post('http://localhost:3101/api/v1/endpoint', json={'key': 'value'}, headers={'Authorization': 'Bearer TOKEN'}); print(r.json())"`

## Critical Rules

- **NEVER kill or interact with port 3100** - This port is reserved for human developers only!
- **Always use port 3101 for agent testing** - The `just agent-start` command automatically uses port 3101
- **Never create test files** - We are in prototype mode. No tests are needed yet. If testing is absolutely necessary for some reason, ask for permission first

