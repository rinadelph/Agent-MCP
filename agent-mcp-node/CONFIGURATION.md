# Agent-MCP Pre-Launch Configuration TUI

This document describes the interactive pre-launch TUI that asks you to configure your tools and settings **before** the server starts, giving you complete control over which features to enable.

## How It Works

1. **Run the server**: `npm run server`
2. **TUI appears** before server starts
3. **Choose your configuration** with interactive menus
4. **Server starts** with exactly what you selected

## Configuration Options

The TUI provides multiple ways to configure your setup:

### 🚀 **Quick Start** 
- One-click setup with recommended Memory + RAG mode
- Perfect for most users who want code assistance
- Lightweight and fast startup

### 🎯 **Predefined Modes**
- Choose from optimized configurations
- See tool counts and performance estimates
- Full/Memory+RAG/Minimal/Development modes

### 🔧 **Custom Configuration**
- Pick exactly which tool categories you want
- Granular control over functionality
- See descriptions for each category

### 📊 **Advanced Setup**
- Detailed walkthrough with explanations
- Category-by-category configuration
- Shows dependencies and warnings

## Predefined Modes

### Full Mode (Default)
- **Description**: Complete agent orchestration platform with all features
- **Tools**: 33 tools across 9 categories
- **Use Case**: Full multi-agent development workflows
- **Categories**: All enabled

### Memory + RAG Mode
- **Description**: Lightweight mode focused on knowledge and memory management
- **Tools**: 15 tools across 5 categories  
- **Use Case**: Code assistance with contextual memory but no agent orchestration
- **Categories**: basic, rag, memory, fileManagement, sessionState

### Minimal Mode
- **Description**: Essential tools only for basic functionality
- **Tools**: 1 tool (health check only)
- **Use Case**: Testing, debugging, or as a base for custom configurations
- **Categories**: basic only

### Development Mode  
- **Description**: Development-focused tools without agent management complexity
- **Tools**: Varies, typically 18-20 tools
- **Use Case**: Solo development with RAG and memory but no multi-agent features
- **Categories**: basic, rag, memory, fileManagement, sessionState, assistanceRequest

## Tool Categories

| Category | Description | Tools |
|----------|-------------|--------|
| `basic` | Health checks, system status (always enabled) | 1 |
| `rag` | Vector search, knowledge base, retrieval augmented generation | 2 |
| `memory` | Project context storage, persistent memory | 6 |
| `agentManagement` | Agent creation, termination, lifecycle management | 7 |
| `taskManagement` | Task creation, assignment, workflows | 6 |
| `fileManagement` | File operations, content access | 2 |
| `agentCommunication` | Inter-agent messaging, collaboration | 3 |
| `sessionState` | Session persistence, recovery, state management | 4 |
| `assistanceRequest` | Intelligent assistance routing | 1 |

## CLI Usage

### Interactive Configuration
```bash
# Launch TUI configuration interface
npm run server --config-mode

# Or via built binary
agent-mcp --config-mode
```

### Predefined Modes
```bash
# Use specific mode
npm run server --mode memoryRag
npm run server --mode minimal  
npm run server --mode development
npm run server --mode full

# Skip TUI and use saved/default config
npm run server --no-tui
```

### Environment Variables
```bash
# Skip TUI entirely
AGENT_MCP_SKIP_TUI=true npm run server

# Override specific categories
AGENT_MCP_ENABLE_RAG=false npm run server
AGENT_MCP_ENABLE_AGENTS=true npm run server

# CI/CD environments automatically skip TUI
CI=true npm run server
```

## Configuration File

Configuration is automatically saved to `.agent/tool-config.json`:

```json
{
  "version": "1.0",
  "mode": "memoryRag", 
  "categories": {
    "basic": true,
    "rag": true,
    "memory": true,
    "agentManagement": false,
    "taskManagement": false,
    "fileManagement": true,
    "agentCommunication": false,
    "sessionState": true,
    "assistanceRequest": false
  },
  "lastModified": "2025-01-09T17:30:00.000Z"
}
```

## HTTP API Endpoints

### Health Check with Configuration
```bash
GET /health
```

Response includes configuration information:
```json
{
  "status": "healthy",
  "configuration": {
    "mode": "memoryRag",
    "enabled_categories": ["basic", "rag", "memory", "fileManagement", "sessionState"],
    "total_categories": 9
  },
  "tools": ["health", "ask_project_rag", "get_rag_status", "..."],
  "...": "other health data"
}
```

### Detailed Statistics
```bash
GET /stats
```

Response includes comprehensive configuration details:
```json
{
  "configuration": {
    "mode": "memoryRag",
    "enabled_categories": ["basic", "rag", "memory", "fileManagement", "sessionState"],
    "disabled_categories": ["agentManagement", "taskManagement", "agentCommunication", "assistanceRequest"],
    "total_categories": 9,
    "details": {
      "basic": true,
      "rag": true,
      "memory": true,
      "agentManagement": false,
      "...": "full category details"
    }
  },
  "tools": {
    "total_tools": 15,
    "tool_names": ["health", "ask_project_rag", "..."]
  },
  "...": "other system stats"
}
```

## TUI Interface Features

The interactive TUI provides:

1. **Current Configuration Review** - Shows active mode and enabled categories
2. **Predefined Mode Selection** - Quick setup with common configurations  
3. **Custom Configuration** - Individual category selection with descriptions
4. **Configuration Validation** - Warnings for potentially problematic setups
5. **Impact Assessment** - Memory usage and startup time estimates

### TUI Navigation
- Use arrow keys to navigate options
- Space bar to select/deselect in checkbox lists
- Enter to confirm selections
- The interface provides helpful descriptions for each tool category

## Benefits

### Performance
- **Reduced Memory Usage**: Only load required tools (15 tools vs 33 in minimal setups)
- **Faster Startup**: Fewer imports and initializations (2-6s vs full 6s)
- **Lower Resource Consumption**: Ideal for constrained environments

### Flexibility  
- **Use Case Optimization**: Match configuration to specific needs
- **Gradual Adoption**: Start minimal and add features as needed
- **Environment Adaptation**: Different configs for dev/staging/production

### Usability
- **Interactive Setup**: No need to memorize configuration options
- **Clear Documentation**: Built-in help and descriptions
- **Persistent Settings**: Configuration saved between sessions

## Migration from Previous Versions

Existing installations will:
1. Continue working with full mode (all tools enabled)
2. Show TUI on first run if no configuration exists
3. Can opt-out of TUI with `--no-tui` or `AGENT_MCP_SKIP_TUI=true`

## Advanced Usage

### Custom Mode Creation
While not directly exposed in the TUI, you can manually edit `.agent/tool-config.json` to create custom configurations that don't match any predefined mode.

### Integration with CI/CD
```yaml
# GitHub Actions example
env:
  CI: true
  AGENT_MCP_SKIP_TUI: true
run: |
  npm run server --mode minimal --no-tui
```

### Docker Deployment
```dockerfile
ENV AGENT_MCP_SKIP_TUI=true
ENV AGENT_MCP_ENABLE_RAG=true
ENV AGENT_MCP_ENABLE_MEMORY=true
CMD ["npm", "run", "server", "--no-tui"]
```

## Troubleshooting

### Configuration Issues
- Use `--mode full` to reset to default configuration
- Delete `.agent/tool-config.json` to force TUI on next startup
- Check `/health` endpoint to verify current configuration

### TUI Not Showing
- Ensure you're not in CI environment (`CI` env var)
- Check that `AGENT_MCP_SKIP_TUI` is not set to `true`
- Use `--config-mode` to force TUI launch

### Permission Issues
- Ensure write access to `.agent/` directory
- Configuration requires ability to create/modify files in project directory

## Implementation Details

The system uses:
- **Dynamic imports** for conditional tool loading
- **Zod schemas** for configuration validation  
- **Commander.js** for CLI argument parsing
- **Inquirer.js** for interactive TUI interface
- **JSON persistence** for configuration storage

This enables flexible, performant, and user-friendly tool configuration management.