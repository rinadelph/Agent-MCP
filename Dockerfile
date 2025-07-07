  # Multi-stage build for Agent-MCP
  FROM node:18-slim as node-base

  # Install Node.js dependencies for dashboard
  WORKDIR /app/dashboard
  COPY agent_mcp/dashboard/package*.json ./
  RUN npm install

  # Main application stage
  FROM python:3.11-slim

  # Set working directory
  WORKDIR /app

  # Set environment variables
  ENV PYTHONUNBUFFERED=1
  ENV PYTHONDONTWRITEBYTECODE=1
  ENV PATH="/app/.venv/bin:/root/.local/bin:$PATH"

  # Install system dependencies including Node.js
  RUN apt-get update && apt-get install -y \
      git \
      curl \
      build-essential \
      && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
      && apt-get install -y nodejs \
      && rm -rf /var/lib/apt/lists/*

  # Install uv (modern Python package manager)
  RUN pip install uv

  # Copy the entire project
  COPY . .

  # Copy Node.js dependencies from previous stage
  COPY --from=node-base /app/dashboard/node_modules ./agent_mcp/dashboard/node_modules

  # Create Python virtual environment and install dependencies
  RUN uv venv .venv && \
    . .venv/bin/activate && \
    uv pip install -e .

  # Copy environment template
  RUN cp .env.example .env

  # Create a non-root user for security
  RUN useradd --create-home --shell /bin/bash agent && \
      chown -R agent:agent /app
  USER agent

  # Expose ports for both the MCP server and dashboard
  EXPOSE 8000 3847

  # Health check for the main server
  HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
      CMD curl -f http://localhost:8000/ || exit 1

  # Default command to start the MCP server (dashboard needs to be started separately)
  CMD ["uv", "run", "-m", "agent_mcp.cli", "--project-dir", "/app"]