# Sebastian's Claude Code Marketplace

Private marketplace for Claude Code skills, plugins, agents, and tooling.

## Installation

```bash
# Add marketplace
/plugin marketplace add sebastian/sebastian-claude-marketplace

# Install plugins
/plugin install <plugin-name>@sebastian-marketplace
```

## Structure

```
.
├── plugins/           # Full plugins with commands, agents, hooks
├── skills/            # Standalone skills
├── templates/         # Generator templates
├── scripts/           # Generator and utility scripts
└── docs/              # Documentation
```

## Creating New Components

```bash
# Create a new skill
./scripts/new-skill.sh my-skill-name

# Create a new plugin
./scripts/new-plugin.sh my-plugin-name

# Create a new agent
./scripts/new-agent.sh my-agent-name

# Create a new command
./scripts/new-command.sh my-command-name
```
