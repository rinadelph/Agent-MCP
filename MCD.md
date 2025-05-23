## 1. Overview & Goals

*   **Objective:** High-level goal (e.g., "Implement user auth," "Create product page").
*   **Scope:** Define what's included/excluded.
*   **Success Criteria:** Testable conditions for completion (e.g., "User can log in," "API returns data").

---

## 2. Context & Architecture

*   **Overall System Context:** Where this fits in the main application. Reference other MCDs/diagrams.
*   **Mermaid Architecture Diagram(s):**
    ```mermaid
    graph TD;
      A --> B;
    ```
    *   *(Brief explanation of relevant diagram parts).*
*   **Technology Stack:** List required tech (e.g., React, Node.js, CSS Modules, Postgres).
*   **Key Concepts & Terminology:** Define essential terms.

---

## 3. Functional Requirements / User Stories

*   **Requirement/Story 1:** [e.g., As a user, I want to...]
    *   **Acceptance Criteria:** Specific, testable conditions (AC1, AC2...).
*   **Requirement/Story 2:** [...]

---

## 4. Design Specification

*   **4.1. UI/UX Design (Frontend):**
    *   Link/description of wireframes/mockups.
    *   List UI components (e.g., `LoginForm`, `Button`).
    *   Styling notes (design system, CSS specifics).
*   **4.2. API Design (Backend/Shared):**
    *   Endpoint(s) & Method(s) (e.g., `POST /api/auth/login`).
    *   Request/Response Schemas (JSON examples).
    *   Error response details.
*   **4.3. Data Model / Schema (Backend):**
    *   Relevant Database Table(s)/Collections.
    *   Schema definition (SQL, ORM interface, etc.).
*   **4.4. Logic & Flow:**
    *   Core algorithms, state logic, business rules.
    *   Mermaid sequence/flow diagrams or pseudo-code for clarity.

---

## 5. Implementation Details & File Structure

*   **Target Directory/Module:** Base path (e.g., `/src/features/auth`).
*   **File Structure Plan:** Define expected files/folders.
    ```
    /src/feature/
    ├── component.tsx
    └── service.ts
    ```
*   **Dependencies:** Required libraries/packages for this task.
*   **Environment Variables:** Needed env vars (e.g., `API_KEY`).

---

## 6. Implementation Units & Tasks (Agent Instructions)

*   **Unit 1: [Task Name, e.g., Create User Model]**
    *   **File(s):** [Target file path(s)]
    *   **Purpose:** [Brief goal of this unit]
    *   **Agent Task(s):**
        1.  `ACTION`: [Specific instruction, e.g., `CREATE_FILE`, `WRITE_CODE`, `IMPORT_DEPENDENCY`]
        2.  `ACTION`: [...]
        3.  `ADD_CODE_SAMPLE` (Optional):
            ```typescript
            // Relevant code snippet
            ```
*   **Unit 2: [Task Name]**
    *   [...]

---

## 7. Relationships & Dependencies

*   **Internal Dependencies:** Links between Units in this MCD.
*   **External Dependencies:** Links to other MCDs or existing code.
*   **Data Flow Summary:** Brief overview of data movement.

---

## 8. Testing Notes (Optional)

*   **Unit Tests:** Key items to test.
*   **Integration Tests:** Scenarios for testing interactions.
*   **Manual Testing:** Steps if needed.

---

## 9. Agent Instructions & Considerations

*   **Processing Order:** Sequential or parallel unit execution notes.
*   **File Locking:** Reminder to use `check file status`.
*   **Assistance/Partitioning:** Note potential areas for help requests.
*   **Code Style:** Reference linter/formatter rules.
