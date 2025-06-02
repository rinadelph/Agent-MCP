# Python Installation Guide for Agent MCP

This guide helps you install Agent MCP as a Python package that provides the `agent-mcp` command globally.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP
```

### 2. Install the Package

#### Option A: Editable Installation (Recommended for Development)
```bash
pip install -e .
```

This installs Agent MCP in "editable" mode, meaning changes to the source code will be reflected immediately without reinstalling.

**Note:** If you get an error about 'build_editable' hook, upgrade pip and setuptools first:
```bash
pip install --upgrade pip setuptools>=64
pip install -e .
```

#### Option B: Standard Installation
```bash
pip install .
```

This creates a standard installation. You'll need to reinstall after any updates.

### 3. Verify Installation

```bash
# Check if the command is available
agent-mcp --version

# View available commands
agent-mcp --help
```

## How It Works

When you run `pip install`, Python:
1. Reads the `pyproject.toml` file
2. Finds the console script entry point: `agent-mcp = "agent_mcp.cli_main:main"`
3. Creates an executable script called `agent-mcp` in your Python's Scripts/bin directory
4. This directory should be in your system's PATH, making `agent-mcp` available globally

## Troubleshooting

### "command not found: agent-mcp"

1. **Check if pip scripts are in PATH:**
   ```bash
   python -m site --user-base
   ```
   The output plus `/bin` (Linux/Mac) or `/Scripts` (Windows) should be in your PATH.

2. **Add to PATH if needed:**
   
   **Linux/macOS (add to ~/.bashrc or ~/.zshrc):**
   ```bash
   export PATH="$PATH:$(python -m site --user-base)/bin"
   ```
   
   **Windows:**
   Add `%APPDATA%\Python\Scripts` to your PATH environment variable.

3. **Try running directly:**
   ```bash
   python -m agent_mcp.cli_main --help
   ```

### Virtual Environment Installation

If you prefer to use a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install Agent MCP
pip install -e .

# The agent-mcp command will only be available when the venv is activated
```

## Updating

To update Agent MCP:

```bash
cd /path/to/Agent-MCP
git pull origin main
pip install -e . --upgrade
```

## Uninstalling

```bash
pip uninstall agent-mcp
```

## Using the Command

Once installed, you can use `agent-mcp` from any directory:

```bash
# Start server for a project
agent-mcp server --project-dir /path/to/your/project

# Index a codebase
agent-mcp index --project-dir /path/to/your/project

# Check database version
agent-mcp migrate --check

# Get help
agent-mcp --help
```