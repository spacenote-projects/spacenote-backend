# SpaceNote API Documentation

## Overview

SpaceNote API is a RESTful API built with FastAPI that provides endpoints for managing spaces, notes, comments, and users.

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
The API uses token-based authentication. After logging in, include the authentication token in the `Authorization` header:

```
Authorization: Bearer <auth_token>
```

Alternatively, the token can be passed as a cookie (automatically set on login).

### Response Format
All successful responses return JSON data. Error responses follow this format:

```json
{
  "message": "Error message describing what went wrong",
  "type": "error_type"  // Optional, for machine parsing (e.g., "authentication_error", "not_found")
}
```

### Common HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid data)
- `401` - Unauthorized (not authenticated)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `500` - Internal Server Error

## Authentication

### Login
`POST /auth/login`

Authenticate with username and password to receive an authentication token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "auth_token": "string"
}
```

**Errors:**
- `401` - Invalid credentials

---

### Logout
`POST /auth/logout`

Invalidate the current authentication session.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

**Errors:**
- `401` - Not authenticated

## Users

### List Users
`GET /users`

Get all users in the system.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response (200):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe"
  }
]
```

**Errors:**
- `401` - Not authenticated

---

### Create User
`POST /users`

Create a new user account. Only accessible by admin users.

**Headers:**
- `Authorization: Bearer <token>` (required - admin)

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe"
}
```

**Errors:**
- `400` - Invalid request (username already exists)
- `401` - Not authenticated
- `403` - Admin privileges required

## Spaces

### List Spaces
`GET /spaces`

Get all spaces where the authenticated user is a member.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response (200):**
```json
[
  {
    "slug": "my-tasks",
    "title": "My Task Tracker",
    "fields": [
      {
        "name": "title",
        "type": "string",
        "required": true,
        "options": {},
        "default": null
      }
    ],
    "members": ["user-id-1", "user-id-2"],
    "created_at": "2025-01-13T10:00:00Z",
    "created_by": "user-id-1"
  }
]
```

**Errors:**
- `401` - Not authenticated

---

### Create Space
`POST /spaces`

Create a new space with the specified slug and title. The authenticated user becomes a member.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Request Body:**
```json
{
  "slug": "my-tasks",
  "title": "My Task Tracker"
}
```

**Response (201):**
```json
{
  "slug": "my-tasks",
  "title": "My Task Tracker",
  "fields": [],
  "members": ["current-user-id"],
  "created_at": "2025-01-13T10:00:00Z",
  "created_by": "current-user-id"
}
```

**Errors:**
- `400` - Invalid request (slug already exists or invalid format)
- `401` - Not authenticated

**Slug Requirements:**
- Lowercase letters, numbers, and hyphens only
- No leading, trailing, or consecutive hyphens
- Pattern: `^[a-z0-9]+(?:-[a-z0-9]+)*$`

---

### Add Field to Space
`POST /spaces/{space_slug}/fields`

Add a new field definition to an existing space. Only space members can add fields.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Path Parameters:**
- `space_slug` - The slug of the space

**Request Body:**
```json
{
  "name": "status",
  "type": "string_choice",
  "required": true,
  "options": {
    "values": ["todo", "in_progress", "done"]
  },
  "default": "todo"
}
```

**Response (200):**
Returns the updated space with the new field added.

**Errors:**
- `400` - Invalid field data or field name already exists
- `401` - Not authenticated
- `403` - Not a member of this space
- `404` - Space not found

## Notes

### List Notes
`GET /spaces/{space_slug}/notes`

Get all notes in a space. Only space members can view notes.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Path Parameters:**
- `space_slug` - The slug of the space

**Response (200):**
```json
[
  {
    "number": 1,
    "space_slug": "my-tasks",
    "fields": {
      "title": "Complete API documentation",
      "status": "in_progress",
      "priority": "high"
    },
    "created_at": "2025-01-13T10:00:00Z",
    "created_by": "user-id",
    "updated_at": "2025-01-13T11:00:00Z"
  }
]
```

**Errors:**
- `401` - Not authenticated
- `403` - Not a member of this space
- `404` - Space not found

---

### Get Note
`GET /spaces/{space_slug}/notes/{number}`

Get a specific note by its number within a space. Only space members can view notes.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Path Parameters:**
- `space_slug` - The slug of the space
- `number` - The note number (auto-incremented within space)

**Response (200):**
```json
{
  "number": 1,
  "space_slug": "my-tasks",
  "fields": {
    "title": "Complete API documentation",
    "status": "in_progress",
    "priority": "high"
  },
  "created_at": "2025-01-13T10:00:00Z",
  "created_by": "user-id",
  "updated_at": "2025-01-13T11:00:00Z"
}
```

**Errors:**
- `401` - Not authenticated
- `403` - Not a member of this space
- `404` - Space or note not found

---

### Create Note
`POST /spaces/{space_slug}/notes`

Create a new note in a space with the provided field values. Only space members can create notes.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Path Parameters:**
- `space_slug` - The slug of the space

**Request Body:**
```json
{
  "raw_fields": {
    "title": "Complete API documentation",
    "description": "Add comprehensive OpenAPI documentation",
    "status": "in_progress",
    "priority": "high"
  }
}
```

**Response (201):**
```json
{
  "number": 1,
  "space_slug": "my-tasks",
  "fields": {
    "title": "Complete API documentation",
    "description": "Add comprehensive OpenAPI documentation",
    "status": "in_progress",
    "priority": "high"
  },
  "created_at": "2025-01-13T10:00:00Z",
  "created_by": "user-id",
  "updated_at": "2025-01-13T10:00:00Z"
}
```

**Errors:**
- `400` - Invalid field data or validation failed
- `401` - Not authenticated
- `403` - Not a member of this space
- `404` - Space not found

**Note:** Field values are provided as raw strings and will be parsed according to their defined types in the space schema.

## Comments

### List Comments
`GET /spaces/{space_slug}/notes/{number}/comments`

Get all comments for a specific note. Only space members can view comments.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Path Parameters:**
- `space_slug` - The slug of the space
- `number` - The note number

**Response (200):**
```json
[
  {
    "id": "comment-id",
    "space_slug": "my-tasks",
    "note_number": 1,
    "content": "This looks good, but we should add more details.",
    "created_by": "user-id",
    "created_at": "2025-01-13T10:30:00Z"
  }
]
```

**Errors:**
- `401` - Not authenticated
- `403` - Not a member of this space
- `404` - Space or note not found

---

### Create Comment
`POST /spaces/{space_slug}/notes/{number}/comments`

Add a new comment to a note. Only space members can create comments.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Path Parameters:**
- `space_slug` - The slug of the space
- `number` - The note number

**Request Body:**
```json
{
  "content": "This looks good, but we should add more details."
}
```

**Response (201):**
```json
{
  "id": "comment-id",
  "space_slug": "my-tasks",
  "note_number": 1,
  "content": "This looks good, but we should add more details.",
  "created_by": "user-id",
  "created_at": "2025-01-13T10:30:00Z"
}
```

**Errors:**
- `401` - Not authenticated
- `403` - Not a member of this space
- `404` - Space or note not found

## Health Check

### Health Status
`GET /health`

Check if the API is running and healthy. No authentication required.

**Response (200):**
```json
{
  "status": "healthy"
}
```

## Field Types Reference

When adding fields to a space, the following field types are available:

### Basic Types
- `string` - Plain text field
- `markdown` - Markdown-formatted text
- `boolean` - True/false value
- `int` - Integer number
- `float` - Decimal number
- `datetime` - Date and time value

### Special Types
- `string_choice` - Single selection from predefined options
  - Requires `options.values` with array of choices
- `tags` - Free-form tags (multiple strings)
- `user` - Reference to a space member

### Field Options
Fields can have the following configuration options:

- `required` (boolean) - Whether the field must have a value
- `default` (any) - Default value for the field
- `options` (object) - Type-specific options:
  - `values` (array) - For `string_choice` type, list of allowed values
  - `min` (number) - For numeric types, minimum allowed value
  - `max` (number) - For numeric types, maximum allowed value

### Example Field Definitions

```json
{
  "name": "title",
  "type": "string",
  "required": true
}
```

```json
{
  "name": "status",
  "type": "string_choice",
  "required": true,
  "options": {
    "values": ["todo", "in_progress", "done", "archived"]
  },
  "default": "todo"
}
```

```json
{
  "name": "priority",
  "type": "int",
  "required": false,
  "options": {
    "min": 1,
    "max": 5
  },
  "default": 3
}
```

```json
{
  "name": "assignee",
  "type": "user",
  "required": false
}
```

```json
{
  "name": "tags",
  "type": "tags",
  "required": false
}
```

## OpenAPI Specification

The API automatically generates an OpenAPI (Swagger) specification available at:
- JSON: `http://localhost:8000/openapi.json`
- Interactive docs: `http://localhost:8000/docs`

This specification can be used to generate client libraries for various programming languages.