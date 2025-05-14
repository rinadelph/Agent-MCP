## 1. Overview & Goals

*   **Objective:** Implement a Multi-Agent Collaboration Protocol (MCP) template for creating and managing multi-agent systems.
*   **Scope:** Python-based MCP server and client implementation with environment variable support, dashboard visualization, and task management.
*   **Success Criteria:** 
    * Server can be started using `uv run -m mcp_template.main --port xxxx --project-dir xxxxx`
    * API keys and configuration use environment variables (no hardcoded values)
    * Agents can connect to the MCP server and collaborate on tasks
    * Dashboard provides visualization of agent interactions

---

## 2. Context & Architecture

*   **Overall System Context:** This MCP template provides a foundation for building multi-agent systems where multiple AI agents collaborate on complex tasks with shared context.
*   **Mermaid Architecture Diagram(s):**
    ```mermaid
    graph TD;
      A[MCP Server] --> B[Database]
      A --> C[Dashboard UI]
      D[Agent 1] --> A
      E[Agent 2] --> A
      F[Agent 3] --> A
      A --> G[RAG System]
      A --> H[Task Manager]
      A --> I[Context Store]
    ```
    *   The MCP Server coordinates all communication between agents and manages shared state. The database stores task information, agent status, and project context. Agents connect to the server via an SSE protocol.
*   **Technology Stack:** Python, OpenAI, SQLite, sqlite-vec, Starlette, Uvicorn, Jinja2, SSE (Server-Sent Events).
*   **Key Concepts & Terminology:** 
    * **MCP (Multi-Agent Collaboration Protocol):** Protocol for agent communication and coordination
    * **Agent:** An AI system that can perform tasks and communicate with other agents
    * **Task:** A unit of work that can be assigned to and completed by agents
    * **Context:** Shared information accessible to all agents
    * **RAG (Retrieval-Augmented Generation):** System for retrieving relevant context for agent tasks

---

## 3. Functional Requirements / User Stories

*   **Requirement 1:** As a developer, I want to set up the MCP environment easily with proper configuration management.
    *   **Acceptance Criteria:** 
        * Environment variables for API keys and server configuration
        * Clear installation instructions
        * Support for `uv` installation
*   **Requirement 2:** As a developer, I want to create and manage agents that can collaborate on tasks.
    *   **Acceptance Criteria:** 
        * Agent creation API
        * Task assignment and status tracking
        * Inter-agent communication
*   **Requirement 3:** As a system administrator, I want to monitor agent activities and task progress.
    *   **Acceptance Criteria:** 
        * Dashboard with agent visualization
        * Task status tracking
        * Activity logging

---

## 4. Design Specification

*   **4.1. UI/UX Design (Frontend):**
    *   Dashboard interface for visualizing agent activities and task status
    *   Components: Agent nodes, Task nodes, Connection visualization, Task tree view
    *   Styled using static CSS files in the static directory
*   **4.2. API Design (Backend/Shared):**
    *   `GET /sse` - Server-Sent Events endpoint for real-time communication
    *   `POST /messages/` - Endpoint for sending messages to agents
    *   `GET /graph_data` - Endpoint for retrieving agent relationship graph data
    *   `GET /task_tree_data` - Endpoint for retrieving task hierarchy data
*   **4.3. Data Model / Schema (Backend):**
    *   **Agents Table:** Stores agent information and status
    *   **Tasks Table:** Stores task information, assignments, and dependencies
    *   **Agent Actions Table:** Logs agent activities and actions
    *   **Project Context Table:** Stores shared project context
    *   **Vector Store:** For RAG functionality using sqlite-vec
*   **4.4. Logic & Flow:**
    *   ```mermaid
        sequenceDiagram
          participant C as Client
          participant S as MCP Server
          participant DB as Database
          participant RAG as RAG System
          
          C->>S: Connect (SSE)
          S->>C: Establish Connection
          C->>S: Request Task
          S->>DB: Check Available Tasks
          DB->>S: Return Tasks
          S->>C: Assign Task
          C->>S: Request Context
          S->>RAG: Query for Relevant Context
          RAG->>S: Return Context
          S->>C: Provide Context
          C->>S: Update Task Status
          S->>DB: Store Task Update
        ```

---

## 5. Implementation Details & File Structure

*   **Target Directory/Module:** `/mcp_template`
*   **File Structure Plan:**
    ```
    /mcp_template/
    ├── __init__.py
    ├── main.py                 # Server implementation
    ├── mcp_client.py           # Client library
    ├── mcp_client_runner.py    # Client runner
    ├── dashboard_api.py        # Dashboard API
    ├── server.py               # Server utilities
    ├── rag_agent_test.py       # Example RAG agent
    ├── static/                 # Static assets
    └── templates/              # HTML templates
        ├── __init__.py
        └── index.html
    ```
*   **Dependencies:** 
    * openai
    * starlette
    * uvicorn
    * jinja2
    * python-dotenv
    * sqlite-vec
    * httpx
    * anyio
    * click
*   **Environment Variables:** 
    * `OPENAI_API_KEY` - OpenAI API key
    * `MCP_SERVER_URL` - MCP server URL
    * `MCP_ADMIN_TOKEN` - (Optional) Admin token
    * `MCP_PROJECT_DIR` - Project directory

---

## 6. Implementation Units & Tasks (Agent Instructions)

*   **Unit 1: Environment Setup**
    *   **File(s):** `pyproject.toml`, `.env`, `.env.example`, `requirements.txt`
    *   **Purpose:** Configure project and environment variables
    *   **Agent Task(s):**
        1.  `CREATE_FILE`: Create pyproject.toml with build configuration
        2.  `CREATE_FILE`: Create .env.example for environment variable template
        3.  `CREATE_FILE`: Create requirements.txt for pip installation
*   **Unit 2: Update Code to Use Environment Variables**
    *   **File(s):** `main.py`, `mcp_client.py`, `rag_agent_test.py`
    *   **Purpose:** Replace hardcoded API keys with environment variables
    *   **Agent Task(s):**
        1.  `MODIFY_FILE`: Update main.py to use python-dotenv
        2.  `MODIFY_FILE`: Update mcp_client.py to use environment variables
        3.  `MODIFY_FILE`: Update rag_agent_test.py to use environment variables
*   **Unit 3: Documentation**
    *   **File(s):** `README.md`, `INSTRUCTIONS.md`
    *   **Purpose:** Provide project documentation and agent instructions
    *   **Agent Task(s):**
        1.  `CREATE_FILE`: Create comprehensive README.md with installation and usage instructions
        2.  `CREATE_FILE`: Create INSTRUCTIONS.md for agent operation guidelines

---

## 7. Relationships & Dependencies

*   **Internal Dependencies:** 
    * main.py depends on dashboard_api.py
    * mcp_client_runner.py depends on mcp_client.py
    * all Python files depend on environment variables
*   **External Dependencies:** 
    * OpenAI API for AI functionality
    * SQLite for database storage
    * sqlite-vec for vector embeddings
*   **Data Flow Summary:** 
    * Clients connect to server via SSE
    * Server manages database state
    * Agents retrieve and update shared context
    * Dashboard visualizes agent relationships and task status

---

## 8. Testing Notes

*   **Unit Tests:** Test environment variable loading, client-server communication
*   **Integration Tests:** Test multi-agent collaboration scenarios
*   **Manual Testing:** Test dashboard visualization, agent task assignment

---

## 9. Agent Instructions & Considerations

*   **Processing Order:** Start with environment setup, then update code, finally create documentation.
*   **File Locking:** Check file status before editing shared files.
*   **Assistance/Partitioning:** Environment variable implementation can be parallelized across different files.
*   **Code Style:** Follow PEP 8 guidelines for Python code.