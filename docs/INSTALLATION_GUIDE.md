# Agent MCP Installation Guide

This guide covers all available installation methods for Agent MCP.

## 🚀 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

## 📦 Standard Installation

```bash
# Clone the repository
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP

# Install with pip (creates the agent-mcp command)
pip install -e .

# Verify installation
agent-mcp --version
```

## 📦 Alternative Installation Methods

### Using uv (Faster Installation)
```bash
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP
uv venv
uv pip install -e .
```

### Non-Editable Install
```bash
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP
pip install .
```

### Development Install with Extras
```bash
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP
pip install -e ".[dev]"
```

## 🔍 Verify Installation

After installation, verify everything is working:

```bash
# Check if command is available
agent-mcp --version

# Run help to see all commands
agent-mcp --help

# Or use the verification script (from the Agent-MCP directory)
python scripts/verify_installation.py
```

## 🎯 Quick Start After Installation

```bash
# 1. Set up your environment
cp .env.example .env
# Edit .env and add your OpenAI API key

# 2. Start the server for your project
agent-mcp server --project-dir /path/to/your/project

# 3. Find your admin token
# Open .agent/mcp_state.db in your project directory
# Check the project_context table

# 4. Initialize agents in your AI assistant
# Follow the instructions in the README
```

## 🛠️ Troubleshooting

### "command not found: agent-mcp"
- **Solution 1**: Restart your terminal
- **Solution 2**: Check if pip scripts are in PATH: `echo $PATH`
- **Solution 3**: Try running directly: `python -m agent_mcp.cli_main`
- **Solution 4**: Reinstall: `pip install -e .`

### "OpenAI API key not found"
- **Solution**: Create `.env` file with `OPENAI_API_KEY=your-key`

### Port already in use
- **Solution**: Use different port: `agent-mcp server --port 9000`

### Installation verification fails
- **Solution**: Run `python scripts/verify_installation.py` for detailed diagnostics

## 📋 System Requirements

- **Node.js**: 14.0.0 or higher (for npm installation)
- **Python**: 3.8 or higher (for pip installation or running from source)
- **Operating System**: Windows, macOS, or Linux
- **Memory**: 4GB RAM minimum
- **Storage**: 500MB free space

## 🔄 Updating Agent MCP

```bash
# Navigate to the Agent-MCP directory
cd /path/to/Agent-MCP

# Pull latest changes
git pull origin main

# Reinstall
pip install -e . --upgrade
```

## 🗑️ Uninstalling

```bash
# Uninstall the package
pip uninstall agent-mcp

# Remove the cloned directory (optional)
rm -rf /path/to/Agent-MCP
```

## 📚 Additional Resources

- [README](../README.md) - Main documentation
- [MCD Examples](../MCD-EXAMPLE/) - Sample Main Context Documents
- [API Reference](./api-reference.md) - Detailed API documentation
- [Contributing](../CONTRIBUTING.md) - How to contribute

## 💬 Getting Help

- **Discord**: [Join our community](https://discord.gg/7Jm7nrhjGn)
- **Issues**: [GitHub Issues](https://github.com/rinadelph/Agent-MCP/issues)
- **Documentation**: See the README and docs folder