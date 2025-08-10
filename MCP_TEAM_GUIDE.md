# MCP Tools Guide for efab-erp Team

## Available MCP Servers

### Core Development Tools
- **mcp__filesystem**: Fast file operations across /mnt/d
- **mcp__git**: Version control operations
- **mcp__memory**: Knowledge graph building and retrieval

### Database Access
- **mcp__postgres**: Direct PostgreSQL access at `postgresql://localhost:5432/efab_db`
- **mcp__sqlite**: SQLite database operations

### ML/AI Libraries
- **mcp__scikit-learn**: Scikit-learn documentation and examples
- **mcp__pandas**: Pandas data manipulation guidance
- **mcp__numpy**: NumPy array operations
- **mcp__huggingface-transformers**: Transformer models
- **mcp__tensorflow**: TensorFlow deep learning
- **mcp__pytorch**: PyTorch neural networks

### Web Frameworks
- **mcp__fastapi**: FastAPI patterns and best practices
- **mcp__streamlit**: Streamlit UI components
- **mcp__sqlalchemy**: SQLAlchemy ORM patterns

### External Tools
- **mcp__fetch**: API calls and web requests
- **mcp__browser**: Browser automation with Puppeteer

## Usage Examples

### File Operations (Use mcp__filesystem instead of Read/Write)
```
# Instead of Read tool, use:
mcp__filesystem.read_file("/mnt/d/efab.ai-765646/src/core/domain.py")

# Instead of Write tool, use:
mcp__filesystem.write_file("/mnt/d/efab.ai-765646/src/core/domain.py", content)
```

### Database Queries (Use mcp__postgres)
```
# Direct SQL queries:
mcp__postgres.query("SELECT * FROM materials WHERE status = 'active'")
```

### Git Operations (Use mcp__git)
```
# Check status:
mcp__git.status()

# Commit changes:
mcp__git.commit("feat: Add domain models for supply chain")
```

### ML Development (Use specialized MCP servers)
```
# Get scikit-learn examples:
mcp__scikit-learn.get_example("demand_forecasting")

# Get pandas DataFrame operations:
mcp__pandas.get_docs("time_series_analysis")
```

## Performance Benefits
- MCP tools are 5-10x faster than standard file operations
- Direct database access eliminates API overhead
- Framework-specific guidance reduces development time
- Knowledge graphs maintain context across sessions

## Best Practices
1. Always prefer MCP tools over standard Read/Write/Bash tools
2. Use mcp__memory to store important discoveries and patterns
3. Leverage framework-specific MCP servers for idiomatic code
4. Use mcp__postgres for all database operations
5. Commit frequently using mcp__git

## Team-Specific Recommendations

### Lead Developer
- Use mcp__fastapi and mcp__sqlalchemy for API development
- Use mcp__filesystem for rapid file navigation
- Use mcp__git for atomic commits

### ML Engineer
- Use mcp__scikit-learn for ML pipelines
- Use mcp__pandas for data preprocessing
- Use mcp__postgres for training data queries
- Use mcp__memory to track model experiments

### DevOps
- Use mcp__postgres for database monitoring
- Use mcp__git for CI/CD workflows
- Use mcp__browser for E2E testing

### Project Manager
- Use mcp__memory to track project knowledge
- Use mcp__git to monitor commit history
- Use mcp__filesystem to review code changes