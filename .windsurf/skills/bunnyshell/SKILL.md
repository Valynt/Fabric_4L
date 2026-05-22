---
skill_id: bunnyshell
name: bunnyshell
version: 1.0.0
description: Manage Bunnyshell cloud environments for development, staging, and production deployments
side_effects: exec
timeout_ms: 300000
required_context: [bunnyshell_config, environment_inventory]
allowed_agents: ["*"]
---

# Bunnyshell Environments Skill

Manage Bunnyshell cloud environments as a Windsurf Skill. This skill enables agents to create, deploy, and manage cloud environments using the Bunnyshell platform via the bns CLI.

## Features

- **Full Environment Lifecycle** - Create, deploy, stop, start, clone, and delete environments
- **Component Management** - View logs, execute commands, and redeploy individual components
- **Remote Development** - SSH access, port forwarding, and debug sessions
- **Pipeline Monitoring** - Track deployments and view pipeline logs
- **Configuration Authoring** - Create and modify bunnyshell.yaml files with proper schema

## Prerequisites

- **Bunnyshell CLI** - Install via Homebrew: `brew install bunnyshell/tap/bunnyshell-cli`
- **API Token** - Get from https://environments.bunnyshell.com/access-token

Configure the CLI:
```bash
bns configure profiles add --name default --token YOUR_TOKEN --default
```

## Usage Examples

### Environment Operations
- "List all my Bunnyshell environments"
- "Deploy environment ENV_ID"
- "Stop the staging environment to save costs"
- "Clone production to create a test environment"

### Component Management
- "Show logs for the api component"
- "Execute a shell command in the database container"
- "Redeploy the frontend component"

### Remote Development
- "SSH into the backend component"
- "Forward port 5432 from the database to my local machine"
- "Start a debug session for the api"

### Configuration
- "Create a bunnyshell.yaml for my Node.js app"
- "Add a PostgreSQL database to my environment config"
- "Export the current environment configuration"

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["list", "deploy", "stop", "start", "clone", "delete", "logs", "exec", "redeploy", "ssh", "port-forward", "config-create", "config-export"]
    },
    "environment_id": { "type": "string" },
    "component_name": { "type": "string" },
    "command": { "type": "string" },
    "config_path": { "type": "string" },
    "service_type": { "type": "string" }
  },
  "required": ["action"]
}
```

## Output Schema

```json
{
  "type": "object",
  "properties": {
    "environments": { "type": "array" },
    "deployment_status": { "type": "string" },
    "logs": { "type": "string" },
    "command_output": { "type": "string" },
    "config_content": { "type": "string" },
    "success": { "type": "boolean" },
    "error": { "type": "string" }
  }
}
```

## Integration with Value Fabric

This skill is particularly useful for:
- Creating ephemeral development environments for feature branches
- Managing staging environments for testing
- Automating production deployments
- Providing isolated environments for tenant onboarding

## Related Files

- `bunnyshell.yaml` - Environment configuration
- `.windsurf/workflows/bunnyshell.md` - Bunnyshell-specific workflows
