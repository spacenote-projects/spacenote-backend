# Architecture

## Tech Stack
- **Python 3.13**
- **MongoDB** - Document database
- **FastAPI** - Web framework

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

### Pure Functions vs Services
- Use pure functions when no state/database needed
- Use services for database, cache, or cross-service operations