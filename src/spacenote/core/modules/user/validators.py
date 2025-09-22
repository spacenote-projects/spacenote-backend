from spacenote.errors import ValidationError


def validate_password(password: str) -> None:
    """Validate password meets requirements.

    Requirements:
    - No whitespace characters
    - Minimum length of 2 characters

    Raises:
        ValidationError: If password doesn't meet requirements
    """
    if len(password) < 2:
        raise ValidationError("Password must be at least 2 characters long")

    if any(char.isspace() for char in password):
        raise ValidationError("Password cannot contain whitespace characters")
