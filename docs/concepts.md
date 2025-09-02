# SpaceNote Concepts

## Overview
SpaceNote is a note-taking system designed for small teams (1-10 users) with AI agent integration capabilities.

## Core Concepts

### Space
A space is a container that groups related notes. Each space represents a project or domain with:
- Unique field schema defining note structure
- Up to 100 spaces per deployment
- Isolated data organization

### Note
Basic content unit within a space. Notes:
- Belong to exactly one space
- Follow space's field schema
- Support various field types

### Fields
Dynamic schema system where each space defines its own fields:
- **Types**: text, number, date, select, multi-select, relation
- **Properties**: required/optional, default values, validation rules
- Fields are space-specific, enabling flexible data modeling

### Users & Permissions
- Small team focus (1-10 users)
- Space-level access control
- Members have full access to their spaces

### Comments
- Threaded discussions on notes
- Support for replies to create conversation threads
- User attribution for all comments
- Timestamp tracking for activity history

### AI Integration
Built with AI agents in mind:
- Structured data format for easy analysis
- API access for agent interactions
- Field types optimized for machine processing
