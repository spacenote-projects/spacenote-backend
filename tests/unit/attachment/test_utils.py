"""Tests for attachment utility functions."""

from spacenote.core.modules.attachment.utils import sanitize_filename


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_normal_filename_unchanged(self):
        """Test that normal filenames pass through safely."""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("photo.jpg") == "photo.jpg"
        assert sanitize_filename("report_2024.xlsx") == "report_2024.xlsx"

    def test_filename_with_spaces(self):
        """Test that filenames with spaces are preserved."""
        assert sanitize_filename("my document.pdf") == "my document.pdf"
        assert sanitize_filename("report final.docx") == "report final.docx"

    def test_multiple_spaces_collapsed(self):
        """Test that multiple consecutive spaces are collapsed to single space."""
        assert sanitize_filename("file    with    spaces.txt") == "file with spaces.txt"

    def test_path_traversal_attack_unix(self):
        """Test that Unix path traversal attempts are neutralized."""
        assert sanitize_filename("../../../etc/passwd") == "passwd"
        assert sanitize_filename("../../secret.txt") == "secret.txt"
        assert sanitize_filename("../file.pdf") == "file.pdf"

    def test_hidden_files_leading_dots_removed(self):
        """Test that leading dots are removed to prevent hidden files."""
        assert sanitize_filename(".hidden") == "hidden"
        assert sanitize_filename("..secret") == "secret"
        assert sanitize_filename("...file.txt") == "file.txt"

    def test_dangerous_characters_replaced(self):
        """Test that dangerous characters are replaced with underscores."""
        assert sanitize_filename("file:name.txt") == "file_name.txt"
        assert sanitize_filename("file*name?.pdf") == "file_name_.pdf"
        assert sanitize_filename('file"name<>.doc') == "file_name_.doc"
        assert sanitize_filename("file|name.txt") == "file_name.txt"

    def test_multiple_underscores_collapsed(self):
        """Test that multiple underscores are collapsed to single underscore."""
        assert sanitize_filename("file___name.txt") == "file_name.txt"
        assert sanitize_filename("a__b__c.pdf") == "a_b_c.pdf"

    def test_multi_extension_files(self):
        """Test that files with multiple extensions are handled correctly."""
        result = sanitize_filename("archive.tar.gz")
        assert result == "archive.tar.gz"
        result = sanitize_filename("backup.tar.bz2")
        assert result == "backup.tar.bz2"

    def test_long_filename_truncated(self):
        """Test that long filenames are truncated to 100 characters."""
        long_name = "a" * 150 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 100
        assert result.endswith(".txt")

    def test_long_filename_preserves_extension(self):
        """Test that extension is preserved when truncating long filenames."""
        long_name = "very_long_filename_" * 10 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 100
        assert result.endswith(".pdf")
        assert result.startswith("very_long_filename")

    def test_long_filename_without_extension(self):
        """Test that filenames without extension are simply truncated."""
        long_name = "x" * 150
        result = sanitize_filename(long_name)
        assert len(result) == 100
        assert result == "x" * 100

    def test_long_extension_handled(self):
        """Test that very long extensions don't break truncation."""
        filename = "file." + "e" * 95
        result = sanitize_filename(filename)
        assert len(result) <= 100

    def test_empty_string_returns_default(self):
        """Test that empty string returns default name."""
        assert sanitize_filename("") == "unnamed_file"

    def test_only_dots_returns_default(self):
        """Test that filename with only dots returns default name."""
        assert sanitize_filename("...") == "unnamed_file"

    def test_only_special_chars_returns_default(self):
        """Test that filename with only special characters returns default name."""
        assert sanitize_filename("***???") == "unnamed_file"
        assert sanitize_filename("///") == "unnamed_file"

    def test_whitespace_only_returns_default(self):
        """Test that whitespace-only filenames return default name."""
        assert sanitize_filename("   ") == "unnamed_file"
        assert sanitize_filename("\t\n") == "unnamed_file"

    def test_unicode_characters_preserved(self):
        """Test that unicode characters in filenames are preserved."""
        assert sanitize_filename("文档.pdf") == "文档.pdf"
        assert sanitize_filename("файл.txt") == "файл.txt"
        assert sanitize_filename("documento.doc") == "documento.doc"

    def test_hyphens_preserved(self):
        """Test that hyphens in filenames are preserved."""
        assert sanitize_filename("my-file-name.pdf") == "my-file-name.pdf"
        assert sanitize_filename("date-2024-01-01.txt") == "date-2024-01-01.txt"

    def test_mixed_attack_vectors(self):
        """Test combination of multiple attack vectors."""
        assert sanitize_filename("../../../.hidden/secret.txt") == "secret.txt"
        assert sanitize_filename("../../dangerous*?.pdf") == "dangerous_.pdf"
