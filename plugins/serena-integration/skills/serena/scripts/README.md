# Serena Bridge Plugin

Python bridge plugin for Serena semantic code navigation.

## Architecture

```
~/.local/bin/serena (bash wrapper)
    ↓
bridge serena <command> (CLI router)
    ↓ HTTP :9100
AI Tool Bridge (FastAPI daemon)
    ├── SerenaPlugin (from scripts/)
    │   ↓ async httpx
    │   Serena MCP Server (:9121, 30+ LSP backends)
    └── JiraPlugin, etc.
```

## Structure

```
scripts/
├── __init__.py      # Exports SerenaPlugin
├── plugin.py        # Plugin class (lifecycle, health)
├── connector.py     # SerenaConnector (circuit breaker)
├── deps.py          # FastAPI dependencies
├── response.py      # Response helpers
├── routes/          # Route modules
│   ├── help.py
│   ├── status.py
│   ├── find.py
│   ├── search.py
│   ├── memory.py
│   ├── edit.py
│   └── onboarding.py
└── serena_cli/      # Core client library
    ├── client.py    # Async client for Serena MCP
    ├── formatters.py
    └── session.py
```

## Usage

```bash
# Via bridge CLI
serena status
serena find Customer
serena refs CustomerRepository src/Repository.php
```

## Configuration

| Setting | Value |
|---------|-------|
| Bridge port | 9100 |
| Serena MCP port | 9121 |
| Entry point | `scripts:SerenaPlugin` |

## API Endpoints

- `GET /serena/help` - CLI help
- `GET /serena/status` - Project status
- `POST /serena/activate` - Activate project
- `GET /serena/find` - Find symbols
- `GET /serena/refs` - Find references
- `GET /serena/overview` - File structure
- `GET /serena/search` - Regex search
- `GET /serena/recipe` - Pre-built searches
- `GET/POST /serena/memory/*` - Memory operations
- `POST /serena/edit/*` - Symbol-based editing
