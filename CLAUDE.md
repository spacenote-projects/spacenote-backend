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

## Testing & Validation

- **NEVER write temporary test scripts** - Do not create one-off Python scripts to test API endpoints
- **NEVER manually test through API calls** - Do not use Python requests or curl to manually verify functionality
- **Only run existing tests** - After code changes, run `just test` to verify nothing broke
- **Let the user test** - The user will test the actual functionality themselves
- **Focus on implementation** - Your job is to write the code, not to verify it works through manual testing

If you want to verify your changes:
1. Run existing automated tests with `just test`
2. That's it. Stop there.

Manual API testing wastes the user's time and provides no value.

## Testing Guidelines

- **Pragmatic coverage** - Don't aim for 100% coverage. Test only useful use cases
- **Human-readable** - Tests must be clear and easy to understand
- **Single responsibility** - Each test method should test ONE specific behavior
- **Class-based organization** - Use classes to group related tests together
- **Descriptive naming** - Test method names should clearly state what is being tested
- **Real-world scenarios** - Focus on testing actual user scenarios, not edge cases for the sake of it
- **Fast execution** - Prefer unit tests that don't require database connections
- **Focused tests** - Keep test methods small (under 15 lines when possible)

## Critical Rules

- **NEVER kill or interact with port 3100** - This port is reserved for human developers only!
- **Always use port 3101 for agent testing** - The `just agent-start` command automatically uses port 3101
- **NEVER disable linter checks without explicit permission** - If a linter warning appears (like RUF006 for asyncio.create_task), you must either:
  1. Fix the issue properly (e.g., store the task reference)
  2. Explain the specific reason why the check needs to be disabled and ask for permission
  - Never silently add `# noqa` comments without explanation

