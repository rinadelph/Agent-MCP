# Configuration Management System

The Agent-MCP system now includes a comprehensive configuration management system that consolidates all hardcoded values, provides schema validation, environment variable validation, and hot-reloading capabilities.

## Features

### ✅ Consolidate Hardcoded Values
All hardcoded values have been moved into a structured configuration system with the following sections:

- **Database Configuration**: File paths, timeouts, connection settings
- **Logging Configuration**: Log levels, file paths, formatting
- **OpenAI Configuration**: API keys, models, tokens, timeouts
- **Agent Configuration**: Agent limits, timeouts, colors
- **RAG Configuration**: Embedding settings, chunking, similarity thresholds
- **Server Configuration**: Host, port, CORS, request limits
- **TMUX Configuration**: Bible rules, compliance settings, monitoring
- **Task Placement Configuration**: RAG settings, thresholds, timeouts
- **System Configuration**: Environment, directories, paths

### ✅ Environment Variable Validation
The system validates required environment variables at startup:

**Required Variables:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `MCP_PROJECT_DIR`: Project directory path

**Optional Variables:**
- `ENVIRONMENT`: Development/production/testing
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `DEBUG`: Enable debug mode
- `SERVER_HOST`: Server host (default: localhost)
- `SERVER_PORT`: Server port (default: 8080)

### ✅ Configuration Schema Validation
All configuration is validated against a JSON schema that ensures:

- Required fields are present
- Data types are correct
- Value ranges are valid
- Nested structures are properly formatted

### ✅ Hot-Reloading Capability
Configuration files can be monitored for changes and automatically reloaded:

```python
# Enable hot-reloading
config_manager.enable_hot_reloading()

# Add change callbacks
def on_config_change(old_config, new_config):
    print("Configuration changed!")

config_manager.add_config_change_callback(on_config_change)
```

## Configuration Sources

The system loads configuration from multiple sources in order of priority:

1. **Environment Variables** (highest priority)
2. **Configuration Files** (JSON/YAML)
3. **Default Values** (lowest priority)

## Configuration File Format

### JSON Format
```json
{
  "database": {
    "file_name": "mcp_state.db",
    "timeout": 30,
    "check_same_thread": false,
    "enable_foreign_keys": true
  },
  "logging": {
    "level": "INFO",
    "file_name": "mcp_server.log",
    "console_enabled": false
  },
  "openai": {
    "api_key": "your-api-key-here",
    "embedding_model": "text-embedding-3-large",
    "embedding_dimension": 1536,
    "chat_model": "gpt-4.1-2025-04-14",
    "max_tokens": 1000000,
    "temperature": 0.4
  },
  "agent": {
    "max_active_agents": 10,
    "agent_idle_timeout": 3600,
    "auto_cleanup_enabled": true,
    "git_commit_interval": 1800
  },
  "rag": {
    "max_context_tokens": 1000000,
    "chunk_size": 2000,
    "overlap_size": 200,
    "similarity_threshold": 0.7,
    "auto_indexing_enabled": true
  },
  "server": {
    "host": "localhost",
    "port": 8080,
    "debug": false,
    "cors_enabled": true
  },
  "tmux": {
    "git_commit_interval": 1800,
    "max_active_agents": 10,
    "credit_conservation_mode": true,
    "strike_system_enabled": true
  },
  "task_placement": {
    "enable_rag": true,
    "duplication_threshold": 0.8,
    "rag_timeout": 5
  },
  "system": {
    "environment": "development"
  }
}
```

### YAML Format
```yaml
database:
  file_name: mcp_state.db
  timeout: 30
  check_same_thread: false
  enable_foreign_keys: true

logging:
  level: INFO
  file_name: mcp_server.log
  console_enabled: false

openai:
  api_key: your-api-key-here
  embedding_model: text-embedding-3-large
  embedding_dimension: 1536
  chat_model: gpt-4.1-2025-04-14
  max_tokens: 1000000
  temperature: 0.4

agent:
  max_active_agents: 10
  agent_idle_timeout: 3600
  auto_cleanup_enabled: true
  git_commit_interval: 1800

rag:
  max_context_tokens: 1000000
  chunk_size: 2000
  overlap_size: 200
  similarity_threshold: 0.7
  auto_indexing_enabled: true

server:
  host: localhost
  port: 8080
  debug: false
  cors_enabled: true

tmux:
  git_commit_interval: 1800
  max_active_agents: 10
  credit_conservation_mode: true
  strike_system_enabled: true

task_placement:
  enable_rag: true
  duplication_threshold: 0.8
  rag_timeout: 5

system:
  environment: development
```

## CLI Configuration Tool

A command-line tool is provided for configuration management:

### Installation
```bash
# Make the CLI executable
chmod +x agent_mcp/utils/config_cli.py
```

### Usage Examples

**Validate Configuration:**
```bash
python -m agent_mcp.utils.config_cli validate
python -m agent_mcp.utils.config_cli validate --config config.json
```

**Export Configuration:**
```bash
python -m agent_mcp.utils.config_cli export config.json
python -m agent_mcp.utils.config_cli export config.yaml --yaml
```

**Import Configuration:**
```bash
python -m agent_mcp.utils.config_cli import config.json
```

**Show Configuration:**
```bash
python -m agent_mcp.utils.config_cli show
python -m agent_mcp.utils.config_cli show openai
```

**Set Configuration Values:**
```bash
python -m agent_mcp.utils.config_cli set openai.temperature 0.7
python -m agent_mcp.utils.config_cli set server.port 9000
```

**Create Default Configuration:**
```bash
python -m agent_mcp.utils.config_cli create-default config.json
python -m agent_mcp.utils.config_cli create-default config.yaml --yaml
```

**Check Environment:**
```bash
python -m agent_mcp.utils.config_cli check-env
```

## Programmatic Usage

### Basic Usage
```python
from agent_mcp.core.config import config_manager

# Access configuration
api_key = config_manager.openai.api_key
max_agents = config_manager.agent.max_active_agents
log_level = config_manager.logging.level
```

### Hot-Reloading
```python
from agent_mcp.core.config import config_manager

# Enable hot-reloading
config_manager.enable_hot_reloading()

# Add change callback
def on_config_change(old_config, new_config):
    print("Configuration changed!")
    # Handle configuration changes

config_manager.add_config_change_callback(on_config_change)
```

### Custom Configuration Manager
```python
from agent_mcp.core.config import ConfigurationManager
from pathlib import Path

# Create custom configuration manager
config_file = Path("custom_config.json")
manager = ConfigurationManager(config_file)

# Enable hot-reloading for custom config
manager.enable_hot_reloading(config_file.parent)
```

## Environment Variables Reference

### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `MCP_PROJECT_DIR` | Project directory path | `/path/to/project` |

### Optional Variables
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ENVIRONMENT` | Environment type | `development` | `production` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `DEBUG` | Enable debug mode | `false` | `true` |
| `SERVER_HOST` | Server host | `localhost` | `0.0.0.0` |
| `SERVER_PORT` | Server port | `8080` | `9000` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-large` | `text-embedding-ada-002` |
| `OPENAI_CHAT_MODEL` | Chat model | `gpt-4.1-2025-04-14` | `gpt-4o` |
| `MAX_ACTIVE_AGENTS` | Max active agents | `10` | `5` |
| `AGENT_IDLE_TIMEOUT` | Agent idle timeout (seconds) | `3600` | `1800` |
| `RAG_CHUNK_SIZE` | RAG chunk size | `2000` | `1000` |
| `RAG_SIMILARITY_THRESHOLD` | RAG similarity threshold | `0.7` | `0.8` |

### TMUX Bible Variables
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `TMUX_GIT_COMMIT_INTERVAL` | Git commit interval (seconds) | `1800` | `900` |
| `TMUX_MAX_ACTIVE_AGENTS` | Max active agents | `10` | `5` |
| `TMUX_CREDIT_CONSERVATION` | Credit conservation mode | `true` | `false` |
| `TMUX_STRIKE_SYSTEM_ENABLED` | Strike system enabled | `true` | `false` |
| `TMUX_AUTO_COMMIT_ENABLED` | Auto commit enabled | `true` | `false` |

## Migration Guide

### From Old Configuration
If you have existing configuration scattered throughout the codebase:

1. **Identify hardcoded values** in your code
2. **Map them to configuration sections** using the schema above
3. **Set environment variables** or create configuration files
4. **Update code** to use `config_manager` instead of hardcoded values

### Example Migration
**Before:**
```python
# Hardcoded values
DB_FILE_NAME = "mcp_state.db"
MAX_AGENTS = 10
OPENAI_MODEL = "gpt-4.1-2025-04-14"
```

**After:**
```python
from agent_mcp.core.config import config_manager

# Configuration-driven values
db_file = config_manager.database.file_name
max_agents = config_manager.agent.max_active_agents
openai_model = config_manager.openai.chat_model
```

## Troubleshooting

### Common Issues

**Configuration validation fails:**
- Check that all required fields are present
- Verify data types match the schema
- Ensure value ranges are valid

**Environment variables not found:**
- Use `python -m agent_mcp.utils.config_cli check-env` to diagnose
- Set required environment variables
- Check variable names and values

**Hot-reloading not working:**
- Ensure the configuration file exists
- Check file permissions
- Verify the file format (JSON/YAML)

**Configuration changes not taking effect:**
- Restart the application after configuration changes
- Check that the configuration file is being loaded
- Verify the configuration file path

### Debug Mode
Enable debug mode to see detailed configuration loading:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python your_script.py
```

## Best Practices

1. **Use environment variables** for sensitive data (API keys, passwords)
2. **Use configuration files** for application settings
3. **Validate configuration** at startup
4. **Enable hot-reloading** in development
5. **Use the CLI tool** for configuration management
6. **Document custom configurations** in your project
7. **Version control configuration templates** but not sensitive data
8. **Test configuration changes** in a safe environment

## Schema Reference

The complete JSON schema for configuration validation is defined in `agent_mcp/core/config.py` as `CONFIG_SCHEMA`. This schema ensures all configuration is properly structured and validated.
