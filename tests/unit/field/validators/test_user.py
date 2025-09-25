"""Tests for USER field validator."""

from uuid import UUID

import pytest

from spacenote.core.modules.field.models import FieldType, SpaceField, SpecialValue
from spacenote.core.modules.field.validators import UserValidator
from spacenote.core.modules.user.models import User
from spacenote.errors import ValidationError


class TestUserFieldDefinition:
    """Tests for user field definition validation."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for all tests in this class."""
        self.validator = UserValidator(mock_space, mock_members)
        self.validator.current_user_id = mock_members[0].id  # Set current user

    def test_basic_user_field_definition(self):
        """Test basic user field definition without default."""
        field = SpaceField(id="assignee", type=FieldType.USER, required=True)
        result = self.validator.validate_field_definition(field)
        assert result.id == "assignee"
        assert result.type == FieldType.USER
        assert result.required is True
        assert result.default is None

    def test_user_field_with_me_default(self):
        """Test user field with $me special value as default."""
        field = SpaceField(id="owner", type=FieldType.USER, default=SpecialValue.ME)
        result = self.validator.validate_field_definition(field)
        assert result.default == SpecialValue.ME

    def test_user_field_with_uuid_default(self):
        """Test user field with UUID string as default."""
        user_id = "87654321-4321-8765-4321-876543218765"
        field = SpaceField(id="reviewer", type=FieldType.USER, default=user_id)
        result = self.validator.validate_field_definition(field)
        # The validator doesn't convert UUID string to UUID object, just validates it exists
        assert result.default == user_id

    def test_user_field_with_username_default(self):
        """Test user field with username as default."""
        field = SpaceField(id="author", type=FieldType.USER, default="testuser")
        result = self.validator.validate_field_definition(field)
        # Username should be converted to UUID
        assert result.default == UUID("87654321-4321-8765-4321-876543218765")

    def test_invalid_uuid_default_raises_error(self):
        """Test that invalid UUID as default raises error."""
        field = SpaceField(id="assignee", type=FieldType.USER, default="99999999-9999-9999-9999-999999999999")
        with pytest.raises(ValidationError, match="not a member of this space"):
            self.validator.validate_field_definition(field)

    def test_invalid_username_default_raises_error(self):
        """Test that non-existent username as default raises error."""
        field = SpaceField(id="assignee", type=FieldType.USER, default="nonexistent")
        with pytest.raises(ValidationError, match="not found or not a member"):
            self.validator.validate_field_definition(field)


class TestUserFieldParsing:
    """Tests for parsing user field values."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator and field for parsing tests."""
        self.validator = UserValidator(mock_space, mock_members)
        self.validator.current_user_id = mock_members[0].id
        self.field = SpaceField(id="assignee", type=FieldType.USER, required=True)
        self.validated_field = self.validator.validate_field_definition(self.field)

    def test_parse_valid_uuid(self):
        """Test parsing valid UUID string."""
        user_id = "87654321-4321-8765-4321-876543218765"
        result = self.validator.parse_value(self.validated_field, user_id)
        assert result == UUID(user_id)

    def test_parse_valid_username(self):
        """Test parsing valid username."""
        result = self.validator.parse_value(self.validated_field, "testuser")
        assert result == UUID("87654321-4321-8765-4321-876543218765")

    def test_parse_me_special_value(self):
        """Test parsing $me special value."""
        result = self.validator.parse_value(self.validated_field, SpecialValue.ME)
        assert result == self.validator.current_user_id

    def test_parse_none_required_field_raises_error(self):
        """Test that None value for required field raises error."""
        with pytest.raises(ValidationError, match="Required field"):
            self.validator.parse_value(self.validated_field, None)

    def test_parse_empty_string_required_field_raises_error(self):
        """Test that empty string for required field raises error."""
        # Empty string is treated as username lookup which fails
        with pytest.raises(ValidationError, match="not found or not a member"):
            self.validator.parse_value(self.validated_field, "")

    def test_parse_none_optional_field(self):
        """Test that None value for optional field returns None."""
        optional_field = SpaceField(id="reviewer", type=FieldType.USER, required=False)
        validated = self.validator.validate_field_definition(optional_field)
        assert self.validator.parse_value(validated, None) is None

    def test_parse_empty_string_optional_field(self):
        """Test that empty string for optional field returns None."""
        optional_field = SpaceField(id="reviewer", type=FieldType.USER, required=False)
        validated = self.validator.validate_field_definition(optional_field)
        assert self.validator.parse_value(validated, "") is None

    def test_parse_invalid_uuid_raises_error(self):
        """Test that invalid UUID raises error."""
        with pytest.raises(ValidationError, match="not a member of this space"):
            self.validator.parse_value(self.validated_field, "99999999-9999-9999-9999-999999999999")

    def test_parse_invalid_username_raises_error(self):
        """Test that non-existent username raises error."""
        with pytest.raises(ValidationError, match="not found or not a member"):
            self.validator.parse_value(self.validated_field, "nonexistent")


class TestUserFieldMeSpecialValue:
    """Tests for $me special value handling."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for $me tests."""
        self.validator = UserValidator(mock_space, mock_members)
        self.field = SpaceField(id="assignee", type=FieldType.USER, required=True)
        self.validated_field = self.validator.validate_field_definition(self.field)

    def test_me_without_current_user_raises_error(self):
        """Test that using $me without current user context raises error."""
        self.validator.current_user_id = None
        with pytest.raises(ValidationError, match="without a logged-in user context"):
            self.validator.parse_value(self.validated_field, SpecialValue.ME)

    def test_me_with_non_member_current_user_raises_error(self):
        """Test that $me with non-member current user raises error."""
        self.validator.current_user_id = UUID("11111111-1111-1111-1111-111111111111")
        with pytest.raises(ValidationError, match="not a member of this space"):
            self.validator.parse_value(self.validated_field, SpecialValue.ME)

    def test_me_default_without_current_user_context(self):
        """Test that $me default without user context raises error."""
        field_with_default = SpaceField(id="owner", type=FieldType.USER, default=SpecialValue.ME)
        validated = self.validator.validate_field_definition(field_with_default)

        self.validator.current_user_id = None
        with pytest.raises(ValidationError, match="without a logged-in user context"):
            self.validator.parse_value(validated, None)

    def test_me_default_with_valid_current_user(self):
        """Test that $me default works with valid current user."""
        field_with_default = SpaceField(id="owner", type=FieldType.USER, default=SpecialValue.ME)
        validated = self.validator.validate_field_definition(field_with_default)

        self.validator.current_user_id = UUID("87654321-4321-8765-4321-876543218765")
        result = self.validator.parse_value(validated, None)
        assert result == self.validator.current_user_id


class TestUserFieldWithMultipleMembers:
    """Tests with multiple space members."""

    @pytest.fixture
    def multiple_members(self, mock_user):
        """Create multiple mock members."""
        user1 = mock_user
        user2 = User(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            username="anotheruser",
            password_hash="$2b$12$hashed_password",
        )
        user3 = User(
            id=UUID("abcdef01-2345-6789-abcd-ef0123456789"),
            username="thirduser",
            password_hash="$2b$12$hashed_password",
        )
        return [user1, user2, user3]

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, multiple_members):
        """Set up validator with multiple members."""
        self.validator = UserValidator(mock_space, multiple_members)
        self.validator.current_user_id = multiple_members[0].id
        self.members = multiple_members
        self.field = SpaceField(id="assignee", type=FieldType.USER)
        self.validated_field = self.validator.validate_field_definition(self.field)

    def test_parse_different_member_by_uuid(self):
        """Test parsing different member UUIDs."""
        for member in self.members:
            result = self.validator.parse_value(self.validated_field, str(member.id))
            assert result == member.id

    def test_parse_different_member_by_username(self):
        """Test parsing different member usernames."""
        for member in self.members:
            result = self.validator.parse_value(self.validated_field, member.username)
            assert result == member.id

    def test_default_with_different_member_uuid(self):
        """Test field default with different member UUID."""
        field = SpaceField(
            id="reviewer",
            type=FieldType.USER,
            default=str(self.members[1].id)
        )
        result = self.validator.validate_field_definition(field)
        # The validator doesn't convert UUID string to UUID object, just validates it exists
        assert result.default == str(self.members[1].id)

    def test_default_with_different_member_username(self):
        """Test field default with different member username."""
        field = SpaceField(
            id="reviewer",
            type=FieldType.USER,
            default=self.members[2].username
        )
        result = self.validator.validate_field_definition(field)
        assert result.default == self.members[2].id


class TestUserFieldEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for edge case tests."""
        self.validator = UserValidator(mock_space, mock_members)
        self.validator.current_user_id = mock_members[0].id

    def test_malformed_uuid_string(self):
        """Test that malformed UUID string raises appropriate error."""
        field = SpaceField(id="assignee", type=FieldType.USER)
        validated = self.validator.validate_field_definition(field)

        with pytest.raises(ValidationError, match="not found or not a member"):
            self.validator.parse_value(validated, "not-a-uuid")

    def test_partial_uuid_string(self):
        """Test that partial UUID string raises appropriate error."""
        field = SpaceField(id="assignee", type=FieldType.USER)
        validated = self.validator.validate_field_definition(field)

        with pytest.raises(ValidationError, match="not found or not a member"):
            self.validator.parse_value(validated, "12345678")

    def test_username_that_looks_like_uuid(self):
        """Test handling username that could be mistaken for UUID."""
        # This would be parsed as username, not UUID
        field = SpaceField(id="assignee", type=FieldType.USER)
        validated = self.validator.validate_field_definition(field)

        with pytest.raises(ValidationError, match="not found or not a member"):
            self.validator.parse_value(validated, "12345678-1234-5678-1234-567812345678x")

    def test_field_with_uuid_default_and_none_value(self):
        """Test field with UUID default returns default for None value."""
        field = SpaceField(
            id="owner",
            type=FieldType.USER,
            default="87654321-4321-8765-4321-876543218765"
        )
        validated = self.validator.validate_field_definition(field)
        result = self.validator.parse_value(validated, None)
        # The default is returned as-is (string format)
        assert result == "87654321-4321-8765-4321-876543218765"
