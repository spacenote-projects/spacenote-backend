"""Utility functions for Telegram integration."""


def generate_note_url(frontend_url: str, space_slug: str, note_number: int) -> str:
    """Generate a direct URL to a note in the frontend.

    Args:
        frontend_url: Base URL of the frontend application
        space_slug: URL slug of the space
        note_number: Sequential number of the note

    Returns:
        Full URL to the note
    """
    return f"{frontend_url}/s/{space_slug}/notes/{note_number}"


def generate_comment_url(frontend_url: str, space_slug: str, note_number: int, comment_number: int) -> str:
    """Generate a direct URL to a comment in the frontend.

    Args:
        frontend_url: Base URL of the frontend application
        space_slug: URL slug of the space
        note_number: Sequential number of the note
        comment_number: Sequential number of the comment within the note

    Returns:
        Full URL to the comment (with anchor)
    """
    return f"{frontend_url}/s/{space_slug}/notes/{note_number}#comment-{comment_number}"
