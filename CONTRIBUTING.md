# Contributing to Agent-MCP

Thank you for your interest in contributing to Agent-MCP! This guide will help you get started with contributing to our multi-agent collaboration framework.

## 🎯 Project Overview

Agent-MCP is a sophisticated multi-agent collaboration system built on the Model Context Protocol (MCP). Our goal is to enable multiple AI agents to work together efficiently on software development tasks through shared memory, coordinated task management, and real-time visualization.

## 🛠️ Development Setup

### Prerequisites
- **Python 3.10+** with pip or uv
- **Node.js 18.0.0+** (recommended: 22.16.0)
- **npm 9.0.0+** (recommended: 10.9.2)
- **OpenAI API key** for embeddings and RAG
- **Claude Code or Cursor** for AI-assisted development

### Setup Instructions

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Agent-MCP.git
   cd Agent-MCP
   ```

2. **Install Dependencies**
   ```bash
   # Python dependencies
   uv venv && uv pip install -e .
   
   # Dashboard dependencies
   cd agent_mcp/dashboard
   npm install
   cd ../..
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Add your OpenAI API key to .env
   ```

4. **Setup Claude Code Hooks** (Important for multi-agent development)
   ```bash
   ./setup-claude-hooks.sh
   ```

5. **Verify Setup**
   ```bash
   # Run tests
   pytest
   
   # Start server
   uv run -m agent_mcp.cli --project-dir .
   
   # Start dashboard (in new terminal)
   cd agent_mcp/dashboard && npm run dev
   ```

## 🔄 Development Workflow

### Branch Strategy
- `main` - Production-ready code
- `feature/your-feature-name` - New features
- `fix/issue-description` - Bug fixes
- `docs/improvement-description` - Documentation updates

### Making Changes

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Development Guidelines**
   - Follow existing code style and patterns
   - Add tests for new functionality
   - Update documentation as needed
   - Use the multi-agent workflow when possible (see below)

3. **Multi-Agent Development** (Recommended)
   - Use Agent-MCP itself for development
   - Create specialized agents for different tasks
   - Follow the MCD (Main Context Document) approach
   - Document your multi-agent workflow in commit messages

### Code Style

**Python Code:**
- Use `ruff` for linting and formatting
- Follow PEP 8 guidelines
- Run `rye run lint` and `rye run format` before committing

**JavaScript/TypeScript:**
- Use ESLint configuration provided
- Follow existing patterns in the dashboard
- Run `npm run lint` in the dashboard directory

**Testing:**
- Write pytest tests with real objects (no mocking)
- Use function-style tests instead of class-style
- Ensure all tests pass before submitting PR

### Commit Guidelines

- Use conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Examples:
  - `feat(tools): add new file locking mechanism`
  - `fix(hooks): resolve Claude Code hook path issues`
  - `docs(setup): add hook configuration instructions`

## 🐛 Reporting Issues

### Bug Reports
Please include:
- **Environment details** (OS, Python version, Node.js version)
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Error messages** and stack traces
- **Configuration details** (hook setup, environment variables)

### Feature Requests
Please include:
- **Use case description** and motivation
- **Proposed solution** or approach
- **Alternative solutions** considered
- **Impact on existing functionality**

## 🚀 Pull Request Process

1. **Pre-submission Checklist**
   - [ ] All tests pass (`pytest`)
   - [ ] Code is properly formatted (`rye run format`)
   - [ ] No linting errors (`rye run lint`)
   - [ ] Dashboard builds without errors (`npm run build`)
   - [ ] Documentation is updated
   - [ ] Hooks configuration works correctly

2. **PR Description Template**
   ```markdown
   ## Summary
   Brief description of changes
   
   ## Changes Made
   - List of specific changes
   - Include any breaking changes
   
   ## Testing
   - How the changes were tested
   - Any new test cases added
   
   ## Multi-Agent Workflow (if applicable)
   - Description of agents used
   - Task breakdown approach
   - Coordination strategies employed
   
   ## Checklist
   - [ ] Tests pass
   - [ ] Documentation updated
   - [ ] Hooks work correctly
   - [ ] No breaking changes (or clearly documented)
   ```

3. **Review Process**
   - Maintainers will review within 1-2 weeks
   - Address feedback promptly
   - Ensure CI checks pass
   - Squash commits if requested

## 📚 Development Resources

### Key Architecture Components
- **MCP Server** (`agent_mcp/app/`) - Core protocol implementation
- **Tools Registry** (`agent_mcp/tools/`) - Modular tool system
- **RAG System** (`agent_mcp/features/rag/`) - Context management
- **Dashboard** (`agent_mcp/dashboard/`) - Real-time visualization
- **Hooks** (`agent_mcp/hooks/`) - File locking and coordination

### Important Concepts
- **Short-lived agents** with persistent shared memory
- **Linear task decomposition** for predictable execution
- **File-level locking** for conflict prevention
- **RAG-based context** sharing between agents

### Testing Philosophy
- Real objects over mocks for integration testing
- Function-style tests for clarity
- Test multi-agent scenarios when possible
- Verify hook functionality in test environments

## 🤝 Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers learn the system
- Share knowledge about multi-agent development

### Communication Channels
- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - General questions and community sharing
- **Discord** - Real-time community chat and support

### Recognition
Contributors will be:
- Added to the contributors list
- Credited in release notes for significant contributions
- Invited to join the core contributor team for sustained involvement

## 📄 License

By contributing to Agent-MCP, you agree that your contributions will be licensed under the AGPL-3.0 license. This ensures that all improvements benefit the open-source community, even in server/SaaS deployments.

## 🆘 Getting Help

- **Documentation**: Check `/docs` directory and README
- **Setup Issues**: Try the `./setup-claude-hooks.sh` script
- **Multi-Agent Questions**: Look at MCD examples in `/MCD-EXAMPLE`
- **Technical Support**: Open a GitHub issue with detailed information

---

**Thank you for contributing to Agent-MCP!** Your efforts help advance the future of multi-agent AI collaboration.