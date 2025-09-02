# Architecture

## Repository Structure
SpaceNote is organized as a multi-repository project:
- **spacenote-backend** - Python + MongoDB + FastAPI (this repository)
- **spacenote-frontend** - React application

## Tech Stack
- **Python 3.13**
- **MongoDB** - Document database
- **FastAPI** - Web framework

## Project Structure

```
spacenote-backend/
├── docs/                       # Documentation
│   ├── architecture.md         # This file
│   └── concepts.md            # Core domain concepts
├── src/spacenote/             # Main application code
│   ├── core/                  # Core business logic
│   │   ├── modules/           # Feature modules
│   │   │   ├── user/         # User management
│   │   │   ├── space/        # Space management
│   │   │   ├── note/         # Note operations
│   │   │   ├── field/        # Field definitions & validation
│   │   │   ├── comment/      # Comment system
│   │   │   ├── session/      # Session management
│   │   │   ├── access/       # Access control
│   │   │   ├── counter/      # ID generation
│   │   │   └── filter/       # Query filters
│   │   ├── core.py           # Core container & DI
│   │   └── db.py             # Database utilities
│   ├── web/                  # Web layer
│   │   ├── routers/          # FastAPI route handlers
│   │   │   ├── auth.py       # Authentication endpoints
│   │   │   ├── users.py      # User endpoints
│   │   │   ├── spaces.py     # Space endpoints
│   │   │   ├── notes.py      # Note endpoints
│   │   │   └── comments.py   # Comment endpoints
│   │   ├── deps.py           # FastAPI dependencies
│   │   ├── server.py         # FastAPI app setup
│   │   └── error_handlers.py # Global error handling
│   ├── app.py                # Application facade
│   ├── config.py             # Configuration
│   ├── main.py               # Entry point
│   └── errors.py             # Custom exceptions
├── justfile                  # Task automation
└── pyproject.toml           # Project dependencies
```

## Layers

```
FastAPI Routers
      |
      v
   App (Facade)
      |
      v
  Core (Container)
      |
      v
    Services
      |
      v
    MongoDB
```

### 1. FastAPI Routers (`web/routers/`)
Handle HTTP requests, call App methods only.

### 2. App Class (`app.py`)
- Facade for all operations
- Validates user permissions before operations
- Never exposes Core or Services directly

### 3. Core Class (`core.py`)
Container providing:
- `self.config` - Application configuration
- `self.mongo_client` - MongoDB client
- `self.database` - Database instance  
- `self.services` - All service instances

### 4. Services
- Inherit from `Service` base class
- Access other services via `self.core.services`
- Handle database operations and business logic

## Module Structure

Each feature in `core/modules/<feature>/`:

### Required Files
- `models.py` - Domain models
- `service.py` - Service with database/cache operations (when needed)

### Optional Files
- Pure function utilities - Stateless helper functions

## Key Patterns

### Service Discovery
Services auto-register in Core initialization and can access each other:
```python
self.core.services.user.get_user()
self.core.services.space.get_space()
```

### Access Control
App validates permissions before every operation:
- `ensure_authenticated()` - User is logged in
- `ensure_admin()` - User is admin
- `ensure_space_member()` - User belongs to space

### Caching Strategy
The project uses in-memory caches for:
- **Users** - All user data cached
- **Spaces** - All space data cached

This aggressive caching is possible because SpaceNote is designed for self-hosted deployments with:
- Small teams (1-10 users maximum)
- Limited spaces (up to 100 spaces)
- Low memory footprint even with full caching

### Pure Functions vs Services
- Use pure functions when no state/database needed
- Use services for database, cache, or cross-service operations

## OpenAPI Integration
- FastAPI automatically generates OpenAPI specification
- Frontend types are auto-generated from the OpenAPI schema
- Ensures type safety across backend and frontend
- Single source of truth for API contracts