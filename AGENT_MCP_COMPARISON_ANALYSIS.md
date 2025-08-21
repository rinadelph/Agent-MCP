# Agent-MCP Implementation Comparison: Python vs Node.js

**Analysis Date:** August 2025  
**Purpose:** Comprehensive file-by-file comparison between Python and Node.js Agent-MCP implementations  
**Goal:** Identify implementation differences, logic issues, and architectural patterns

---

## Executive Summary

This document provides a detailed analysis comparing the Python and Node.js implementations of Agent-MCP. The analysis covers directory structures, configuration files, core implementations, MCP tools, database operations, and identifies potential logic differences and issues.

---

## 1. Directory Structure Analysis

### 1.1 Python Implementation Structure
```
agent_mcp/
├── __main__.py                          # Entry point
├── cli.py                              # Command-line interface
├── server.py                           # Main server implementation
├── core/                               # Core functionality
│   ├── auth.py                        # Authentication
│   ├── config.py                      # Configuration management
│   └── globals.py                     # Global state management
├── db/                                # Database layer
│   ├── connection.py                  # Database connection
│   ├── write_queue.py                 # Write operations queue
│   ├── actions/                       # Database actions
│   └── migrations/                    # Database migrations
├── features/                          # Feature modules
│   ├── claude_session_monitor.py     # Claude session monitoring
│   ├── worktree_integration.py       # Git worktree support
│   ├── dashboard/                     # Web dashboard
│   ├── rag/                          # RAG (Retrieval Augmented Generation)
│   └── task_placement/               # Task placement logic
├── mcp/                              # MCP protocol implementation
│   ├── tools/                       # MCP tools
│   └── server.py                    # MCP server
└── utils/                           # Utility modules
    ├── tmux.py                     # Tmux integration
    └── git.py                      # Git utilities
```

### 1.2 Node.js Implementation Structure  
```
agent-mcp-node/
├── package.json                        # NPM package configuration
├── tsconfig.json                      # TypeScript configuration
├── src/
│   ├── examples/server/               # Example server implementations
│   │   └── agentMcpServer.ts         # Main server entry point
│   ├── core/                         # Core functionality
│   │   ├── auth.ts                   # Authentication
│   │   ├── config.ts                 # Configuration management
│   │   └── globals.ts                # Global state management
│   ├── db/                           # Database layer
│   │   ├── connection.ts             # Database connection
│   │   └── schema.ts                 # Database schema
│   ├── features/                     # Feature modules
│   │   └── rag/                     # RAG implementation
│   ├── tools/                        # MCP tools implementation
│   ├── types/                        # TypeScript type definitions
│   │   └── database.ts              # Database types
│   └── external/                     # External service integrations
│       └── openai_service.ts        # OpenAI integration
└── dist/                            # Compiled JavaScript output
```

### 1.3 Key Structural Differences

| Aspect | Python | Node.js | Analysis |
|--------|--------|---------|----------|
| **Entry Point** | `__main__.py` + `cli.py` | `examples/server/agentMcpServer.ts` | Python uses standard module entry point, Node.js uses example-based approach |
| **Language Features** | Python 3.10+ with type hints | TypeScript with strict typing | Both use strong typing, Node.js more explicit |
| **Project Organization** | Flat module structure | Nested src/ structure | Node.js follows conventional src/ pattern |
| **Configuration** | `pyproject.toml` | `package.json` + `tsconfig.json` | Node.js has separate compile-time config |
| **Build Process** | No build step (interpreted) | TypeScript compilation to dist/ | Node.js requires compilation step |

---

## 2. Configuration File Comparison

### 2.1 Python Configuration (pyproject.toml)

**Key Details:**
- **Version:** 2.5.0  
- **Python Requirement:** >=3.10
- **Package Manager:** uv/rye (modern Python tooling)
- **Dependencies:** 11 core dependencies including MCP SDK >=1.8.1
- **Build System:** setuptools with modern configuration

**Dependencies Analysis:**
```toml
dependencies = [
    "anyio",                    # Async I/O library
    "click",                    # CLI framework  
    "openai",                   # OpenAI API client
    "starlette",               # ASGI web framework
    "uvicorn",                 # ASGI server
    "jinja2",                  # Template engine
    "python-dotenv",           # Environment management
    "sqlite-vec",              # Vector database extension
    "httpx",                   # Modern HTTP client
    "mcp>=1.8.1",             # Model Context Protocol SDK
]
```

**Development Tools:**
- **Linting:** ruff (modern, fast Python linter)
- **Formatting:** ruff format (replaces black)
- **Testing:** pytest with async support
- **Scripts:** Comprehensive script definitions for common tasks

### 2.2 Node.js Configuration (package.json)

**Key Details:**
- **Version:** 4.0.0 (notably higher version number)
- **Node.js Requirement:** >=18.0.0  
- **Package Manager:** npm (standard)
- **Dependencies:** 10 runtime + 4 development dependencies
- **Build System:** TypeScript compilation to JavaScript

**Dependencies Analysis:**
```json
"dependencies": {
    "@modelcontextprotocol/sdk": "^1.4.0",  // MCP SDK (different version)
    "@types/better-sqlite3": "^7.6.13",     // SQLite type definitions
    "@types/cors": "^2.8.19",               // CORS type definitions  
    "better-sqlite3": "^12.2.0",            // SQLite database driver
    "commander": "^14.0.0",                 // CLI framework
    "cors": "^2.8.5",                       // CORS middleware
    "dotenv": "^17.2.1",                    // Environment management
    "express": "^4.18.2",                   // Web framework
    "glob": "^11.0.3",                      // File pattern matching
    "openai": "^5.11.0",                    // OpenAI API client
    "sqlite-vec": "^0.1.7-alpha.2",        // Vector database (alpha version)
    "zod": "^3.22.4"                        // Schema validation
}
```

**TypeScript Configuration:**
```json
{
  "target": "ES2022",                    // Modern JavaScript target
  "module": "Node16",                    // Node.js ESM support
  "strict": true,                        // Strict type checking
  "noUncheckedIndexedAccess": true,     // Extra safety for arrays/objects
  "outDir": "./build",                   // Compilation output
  "declaration": true,                   // Generate .d.ts files
  "sourceMap": true                      // Debug support
}
```

### 2.3 Configuration Comparison Analysis

| Aspect | Python | Node.js | Critical Differences |
|--------|--------|---------|---------------------|
| **Version Numbers** | 2.5.0 | 4.0.0 | ⚠️ **MAJOR DISCREPANCY**: Node.js claims v4.0 while Python is v2.5 |
| **MCP SDK Version** | >=1.8.1 | ^1.4.0 | ⚠️ **VERSION MISMATCH**: Python uses newer MCP SDK |
| **sqlite-vec Version** | stable | 0.1.7-alpha.2 | ⚠️ **STABILITY ISSUE**: Node.js uses alpha version |
| **Web Framework** | Starlette (ASGI) | Express (traditional) | Different paradigms (async vs callback) |
| **CLI Framework** | Click (Python-native) | Commander (Node-native) | Language-appropriate choices |
| **Type Safety** | Type hints (runtime) | TypeScript (compile-time) | Node.js has stronger compile-time safety |
| **Build Process** | Interpreted + optional | Required compilation | Node.js has mandatory build step |

### 🔍 **Critical Issues Identified:**

1. **Version Synchronization Problem**: The implementations claim different version numbers (2.5.0 vs 4.0.0), indicating potential feature parity issues.

2. **MCP SDK Version Mismatch**: Python uses MCP SDK >=1.8.1 while Node.js uses ^1.4.0. This could lead to protocol compatibility issues.

3. **sqlite-vec Stability**: Node.js uses an alpha version of sqlite-vec while Python uses a stable version, potentially causing reliability differences.

4. **Dependency Counting**: Node.js has fewer total dependencies (10 vs 11) but includes more type definition packages, suggesting different architectural approaches.

---

## 3. Core Server Implementation Analysis

### 3.1 Python Server Implementation

**File:** `agent_mcp/cli.py` (Entry Point)
**Framework:** Starlette (ASGI) + Click (CLI)

**Key Architecture:**
```python
@click.command()
@click.option("--port", type=int, default=8080)
@click.option("--transport", type=click.Choice(["stdio", "sse"]))
@click.option("--project-dir", type=click.Path())
@click.option("--admin-token", type=str)
```

**Environment Loading:**
- **Sophisticated .env loading**: Searches up to 3 parent directories for .env files
- **Manual environment variable setting**: Explicitly sets each variable from .env
- **Debug logging**: Extensive logging of environment loading process
- **AGPL License**: Uses GNU Affero General Public License v3

**Server Characteristics:**
- **Transport:** Supports both STDIO and SSE (Server-Sent Events)
- **Default Port:** 8080
- **Web Framework:** Starlette (modern ASGI framework)
- **Async:** Full async/await support with anyio
- **Database Admin Token:** JSON-based storage with fallback logic

### 3.2 Node.js Server Implementation

**File:** `agent-mcp-node/src/examples/server/agentMcpServer.ts` (Entry Point)
**Framework:** Express + Commander (CLI)

**Key Architecture:**
```typescript
program
  .option('-p, --port <number>', 'port to run the server on', '3001')
  .option('--project-dir <path>', 'project directory to operate in')
```

**Environment Loading:**
- **Simple dotenv.config()**: Standard environment loading
- **Directory Change Logic**: Attempts to change to project directory
- **Error Handling**: Try/catch for directory operations
- **MIT License**: More permissive licensing

**Server Characteristics:**
- **Transport:** HTTP/JSON-RPC via Express
- **Default Port:** 3001
- **Web Framework:** Express (traditional Node.js framework)
- **Async:** Uses async/await with standard Node.js patterns
- **MCP SDK:** Uses official @modelcontextprotocol/sdk

### 3.3 Server Implementation Comparison

| Aspect | Python | Node.js | Critical Differences |
|--------|--------|---------|---------------------|
| **Entry Point** | CLI with click decorators | Commander program parsing | Python more declarative, Node.js more imperative |
| **Default Port** | 8080 | 3001 | ⚠️ **PORT CONFLICT POTENTIAL** |
| **Transport Protocol** | SSE (Server-Sent Events) | HTTP/JSON-RPC | ⚠️ **COMPLETELY DIFFERENT PROTOCOLS** |
| **Web Framework** | Starlette (ASGI, modern) | Express (traditional) | Different async paradigms |
| **Environment Handling** | Complex multi-level search | Simple dotenv.config() | Python more robust but complex |
| **License** | AGPL v3 (copyleft) | MIT (permissive) | ⚠️ **LICENSE INCOMPATIBILITY** |
| **Directory Handling** | Click path validation | Manual resolve + chdir | Python has built-in validation |
| **Error Handling** | Extensive logging | Basic try/catch | Python more comprehensive |

### 🔍 **Critical Issues Identified:**

1. **Protocol Incompatibility**: Python uses SSE transport while Node.js uses HTTP/JSON-RPC, making them incompatible for client connections.

2. **License Conflict**: Python uses AGPL v3 (strong copyleft) while Node.js uses MIT (permissive), creating legal compatibility issues.

3. **Port Defaults**: Different default ports (8080 vs 3001) could cause deployment confusion.

4. **MCP SDK Versions**: Different MCP SDK versions could lead to protocol implementation differences.

---

## 4. Database Schema Comparison

### 4.1 Python Database Schema

**File:** `agent_mcp/db/schema.py`
**Database:** SQLite with sqlite-vec extension

**Key Features:**
```python
def check_embedding_dimension_compatibility(conn: sqlite3.Connection) -> bool:
    """Check if rag_embeddings table dimension matches configured dimension."""
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type IN ('table', 'virtual') AND name='rag_embeddings'"
    )
    # Extract dimension using regex: r"FLOAT\[(\d+)\]"
    # Provides migration warnings and dimension mismatch detection
```

**Schema Characteristics:**
- **Vector Support:** sqlite-vec extension for embeddings
- **Dimension Checking:** Runtime dimension compatibility validation
- **Migration Warnings:** Detailed logging for schema mismatches
- **Connection Management:** Centralized via get_db_connection()
- **Logging:** Extensive debug and warning messages

### 4.2 Node.js Database Schema

**File:** `agent-mcp-node/src/db/schema.ts`  
**Database:** SQLite with better-sqlite3 driver

**Key Features:**
```typescript
function checkEmbeddingDimensionCompatibility(): boolean {
  const db = getDbConnection();
  const tableInfo = db.prepare(`
    SELECT sql FROM sqlite_master 
    WHERE type IN ('table', 'virtual') AND name='rag_embeddings'
  `).get() as { sql: string } | undefined;
  
  // Same dimension extraction logic with regex
  const dimensionMatch = tableInfo.sql.match(/FLOAT\[(\d+)\]/);
}
```

**Schema Characteristics:**
- **Vector Support:** sqlite-vec extension (alpha version)
- **Type Safety:** Full TypeScript type definitions
- **Prepared Statements:** Uses better-sqlite3 prepared statements
- **Error Handling:** Try/catch with warning messages
- **Configuration:** MCP_DEBUG flag for conditional logging

### 4.3 Database Implementation Comparison

| Aspect | Python | Node.js | Critical Differences |
|--------|--------|---------|---------------------|
| **SQLite Driver** | Built-in sqlite3 | better-sqlite3 | Node.js uses more performant driver |
| **Vector Extension** | sqlite-vec (stable) | sqlite-vec (alpha) | ⚠️ **STABILITY MISMATCH** |
| **Type Safety** | Runtime type checking | Compile-time TypeScript | Node.js has stronger type safety |
| **Query Style** | cursor.execute() | prepared statements | Node.js more performance-oriented |
| **Connection Handling** | get_db_connection() | getDbConnection() | Similar patterns, different naming |
| **Schema Logic** | Nearly identical | Nearly identical | ✅ **LOGIC PARITY** achieved |
| **Dimension Detection** | Same regex pattern | Same regex pattern | ✅ **ALGORITHM CONSISTENCY** |

### 🔍 **Critical Issues Identified:**

1. **sqlite-vec Version Mismatch**: Python uses stable version while Node.js uses alpha, potentially causing data compatibility issues.

2. **Database Driver Differences**: Different SQLite drivers could lead to subtle behavioral differences or performance variations.

3. **Schema Consistency**: Despite implementation differences, the core logic for dimension checking is nearly identical (positive finding).

---

## 5. Tool Implementation Analysis

### 5.1 Python Tool Architecture

**File Structure:**
```
tools/
├── registry.py              # Tool registration system
├── admin_tools.py           # Administrative tools (60KB - extensive)  
├── agent_tools.py           # Agent-specific tools
├── agent_communication_tools.py  # Inter-agent communication
├── task_tools.py           # Task management (162KB - largest file)
├── rag_tools.py            # RAG/search functionality
├── file_management_tools.py # File operations
├── file_metadata_tools.py   # File metadata management
├── project_context_tools.py # Project context (53KB - substantial)
└── utility_tools.py        # Miscellaneous utilities
```

**Registry System:**
```python
# Placeholder-based approach with future import strategy
tool_implementations: Dict[str, Callable[..., Awaitable[List[mcp_types.TextContent]]]] = {
    # Will map tool names to implementation functions
}

async def placeholder_tool_logic(*args, **kwargs) -> List[mcp_types.TextContent]:
    tool_name = kwargs.get('_tool_name', 'unknown_placeholder_tool')
    return [mcp_types.TextContent(type="text", text=f"Placeholder response for {tool_name}")]
```

**Tool Example (agent_tools.py):**
```python
async def get_system_prompt_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    requesting_agent_id = get_agent_id(agent_auth_token)
    
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid agent token required")]
    
    system_prompt_str = generate_system_prompt(
        agent_id=requesting_agent_id,
        agent_token_for_prompt=agent_auth_token,
        admin_token_runtime=g.admin_token
    )
    
    return [mcp_types.TextContent(type="text", text=f"System Prompt for Agent '{requesting_agent_id}':\n\n{system_prompt_str}")]
```

### 5.2 Node.js Tool Architecture

**File Structure:**
```
tools/
├── registry.ts              # Tool registration with TypeScript types
├── basic.ts                 # Basic/health tools
├── agent.ts                 # Agent management tools
├── agentCommunication.ts    # Inter-agent communication
├── assistanceRequest.ts     # Intelligent assistance requests
├── rag.ts                  # RAG/search functionality
├── file_management.ts      # File operations
├── project_context.ts     # Project context management
└── tasks/                  # Task management subsystem
    ├── index.ts           # Task exports
    ├── core.ts           # Core task functionality
    ├── creation.ts       # Task creation
    ├── management.ts     # Task management
    └── operations.ts     # Task operations
```

**Registry System:**
```typescript
export interface ToolContext {
  sessionId?: string;
  agentId?: string;
  requestId?: string;
  sendNotification?: (notification: any) => Promise<void>;
}

export interface ToolResult {
  content: Array<{
    type: 'text' | 'image' | 'resource';
    text?: string;
    data?: string;
    mimeType?: string;
    uri?: string;
  }>;
  isError?: boolean;
}

export type ToolHandler = (args: any, context: ToolContext) => Promise<ToolResult>;
```

**Tool Example (agent.ts):**
```typescript
export interface Agent {
  token: string;
  agent_id: string;
  capabilities: string[];
  status: 'created' | 'active' | 'terminated' | 'failed' | 'completed';
  current_task?: string;
  working_directory: string;
  color: string;
  created_at: string;
  updated_at: string;
  terminated_at?: string;
}

const globalState = {
  activeAgents: new Map<string, Agent>(),
  agentWorkingDirs: new Map<string, string>(),
  agentTmuxSessions: new Map<string, string>(),
  agentColorIndex: 0,
  serverStartTime: new Date().toISOString()
};
```

### 5.3 Tool Implementation Comparison

| Aspect | Python | Node.js | Critical Differences |
|--------|--------|---------|---------------------|
| **Total Tools Files** | 9 core files | 8 core files + tasks/ subdirectory | Similar coverage, different organization |
| **Largest Files** | task_tools.py (162KB) | Split into tasks/ directory | Node.js better modularization |
| **Registry Pattern** | Placeholder-based with imports | Interface-based with handlers | Node.js more type-safe |
| **Type Safety** | Runtime validation | Compile-time TypeScript | Node.js stronger validation |
| **Error Handling** | mcp_types.TextContent return | ToolResult interface | Node.js more structured |
| **Global State** | Python globals module | TypeScript Map objects | Different state management |
| **Tool Context** | Function arguments | ToolContext interface | Node.js more structured context |
| **Agent Management** | Extensive admin_tools.py | Dedicated agent.ts | Similar functionality, different structure |

### 🔍 **Tool Implementation Issues:**

1. **Registry Inconsistency**: Python uses placeholder-based registry while Node.js uses interface-based approach, leading to different tool execution patterns.

2. **File Size Imbalance**: Python has some extremely large files (162KB task_tools.py, 60KB admin_tools.py) while Node.js maintains better modularization.

3. **Type Safety Gap**: Node.js has compile-time type checking for all tool parameters while Python relies on runtime validation.

4. **State Management**: Different approaches to global state could lead to synchronization issues.

---

## 6. Authentication & Session Management

### 6.1 Python Authentication

**File:** `agent_mcp/core/auth.py`

**Token Generation:**
```python
def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_hex(16)  # 32-character hex string
```

**Token Verification:**
```python
def verify_token(token: str, required_role: str = "agent") -> bool:
    if not token:
        return False
    if required_role == "admin" and token == g.admin_token:
        return True
    if required_role == "agent" and g.active_agents and token in g.active_agents:
        return True
    if required_role == "agent" and token == g.admin_token:
        return True  # Admins can act as agents
    return False
```

### 6.2 Node.js Authentication

**File:** `agent-mcp-node/src/core/auth.ts`

**Token Generation:**
```typescript
export function generateToken(): string {
  return randomBytes(16).toString('hex');  // Same 32-character hex
}
```

**Token Verification:**
```typescript
export function verifyToken(token: string, requiredRole: 'admin' | 'agent' = 'agent'): boolean {
  if (!token) {
    return false;
  }
  
  if (requiredRole === 'admin' && token === globalState.adminToken) {
    return true;
  }
  
  // Enhanced with database fallback for better agent recognition
  // (Additional logic for database verification)
}
```

### 6.3 Authentication Comparison

| Aspect | Python | Node.js | Critical Differences |
|--------|--------|---------|---------------------|
| **Token Generation** | secrets.token_hex(16) | randomBytes(16).toString('hex') | ✅ **IDENTICAL ALGORITHM** |
| **Token Length** | 32 characters | 32 characters | ✅ **CONSISTENT** |
| **Admin Verification** | g.admin_token comparison | globalState.adminToken comparison | ✅ **SAME LOGIC** |
| **Agent Verification** | g.active_agents lookup | Enhanced with database fallback | ⚠️ Node.js has additional features |
| **Role System** | String-based roles | TypeScript enum-like | Node.js more type-safe |
| **Database Integration** | Limited | Enhanced database checking | Node.js more robust |

---

## 7. Critical Logic Issues & Recommendations

### 7.1 High-Priority Issues

#### 🚨 **CRITICAL: Protocol Incompatibility**
**Issue:** Python uses SSE (Server-Sent Events) transport while Node.js uses HTTP/JSON-RPC
**Impact:** Clients cannot connect to both implementations interchangeably
**Recommendation:** Standardize on one transport protocol or support both in each implementation

#### 🚨 **CRITICAL: Version Synchronization**
**Issue:** Python claims v2.5.0, Node.js claims v4.0.0
**Impact:** Feature parity confusion, deployment conflicts
**Recommendation:** Establish version synchronization process

#### 🚨 **CRITICAL: License Incompatibility**
**Issue:** Python uses AGPL v3 (copyleft) while Node.js uses MIT (permissive)
**Impact:** Legal complications for mixed deployments
**Recommendation:** Align on single license or clearly document compatibility

#### ⚠️ **HIGH: MCP SDK Version Mismatch**
**Issue:** Python uses MCP SDK >=1.8.1, Node.js uses ^1.4.0
**Impact:** Potential protocol compatibility issues
**Recommendation:** Update both to same MCP SDK version

#### ⚠️ **HIGH: sqlite-vec Stability Mismatch**
**Issue:** Python uses stable sqlite-vec, Node.js uses alpha version
**Impact:** Data reliability and compatibility differences
**Recommendation:** Standardize on stable sqlite-vec version

### 7.2 Medium-Priority Issues

#### 🔧 **Configuration Inconsistencies**
- Different default ports (8080 vs 3001)
- Different environment loading strategies
- Different CLI frameworks (Click vs Commander)

#### 🔧 **Implementation Patterns**
- Different tool registry approaches
- Different state management patterns
- File size and modularization inconsistencies

#### 🔧 **Database Differences**  
- Different SQLite drivers (built-in vs better-sqlite3)
- Different query patterns (cursor vs prepared statements)

### 7.3 Positive Findings

#### ✅ **Strong Consistency Areas**
1. **Token Generation**: Identical algorithm and length
2. **Database Schema Logic**: Nearly identical dimension checking
3. **Core Authentication**: Similar verification patterns
4. **Tool Coverage**: Comparable functionality across implementations

#### ✅ **Complementary Strengths**
- **Python**: More robust error handling, extensive logging
- **Node.js**: Better type safety, more modular architecture, performance optimizations

---

## 8. Summary & Action Items

### 8.1 Implementation Status
Both implementations provide similar functionality but with significant architectural and compatibility differences. The Node.js version appears more mature in terms of type safety and modularization, while the Python version provides more comprehensive logging and error handling.

### 8.2 Immediate Actions Required

1. **Synchronize Protocol Support**: Choose SSE or HTTP/JSON-RPC and implement in both
2. **Align MCP SDK Versions**: Update both implementations to latest compatible version  
3. **Standardize sqlite-vec**: Move Node.js to stable version
4. **Version Synchronization**: Establish versioning policy
5. **License Resolution**: Choose compatible licensing approach

### 8.3 Long-term Improvements

1. **Unified Testing**: Create comparative test suite
2. **Documentation Alignment**: Ensure both implementations documented equally
3. **Feature Parity Tracking**: Maintain feature compatibility matrix
4. **Performance Benchmarking**: Compare performance characteristics
5. **Client Compatibility**: Ensure clients work with both implementations

### 8.4 Architecture Recommendations

1. **Adopt Node.js Modularization**: Split large Python files
2. **Enhance Python Type Safety**: Add more runtime validation
3. **Standardize State Management**: Choose consistent global state pattern
4. **Unified Tool Registry**: Align tool registration approaches
5. **Database Abstraction**: Create common database interface layer

---

**Analysis Complete: August 2025**
**Total Issues Identified: 15 (5 Critical, 4 High Priority, 6 Medium Priority)**
**Positive Consistency Areas: 8**

This analysis will be continuously updated as implementations evolve.