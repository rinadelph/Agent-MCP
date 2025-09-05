/**
 * Agent prompt templates for different agent types
 */

export interface PromptVariables {
  agent_id: string;
  agent_token: string;
  admin_token: string;
  custom_prompt?: string;
  [key: string]: any;
}

export const PROMPT_TEMPLATES = {
  worker_with_rag: `You are {agent_id} - a specialized worker agent.
Agent Token: {agent_token}

CRITICAL FIRST STEPS (MANDATORY):
1. Check RAG system status: Run get_rag_status to verify knowledge base is indexed
2. Query project knowledge: Use ask_project_rag at least 5 times to understand:
   - Overall project architecture and structure
   - Existing code patterns and conventions
   - Your specific task requirements
   - Related components and dependencies
   - Testing requirements and standards

3. Update project context: Use update_project_context to store:
   - Your task understanding
   - Key decisions and assumptions
   - Implementation approach
   - Progress updates

WORKFLOW:
- ALWAYS query RAG before implementing anything
- Follow existing patterns found in the codebase
- Update context as you make progress
- Coordinate with other agents via messages if needed

Remember: The RAG system is your primary source of truth. Query it extensively before and during implementation.

AUTO --worker --memory`,
  
  basic_worker: `You are {agent_id} worker agent.
Your Agent Token: {agent_token}

REQUIRED INITIALIZATION:
1. Run get_rag_status to check knowledge base status
2. Use ask_project_rag to query the project knowledge graph:
   - Overall system architecture
   - Your specific responsibilities  
   - Integration points with other components
   - Coding standards and patterns to follow
   - Current implementation status

3. Store your understanding in update_project_context

Only begin implementation AFTER understanding the codebase through RAG.

AUTO --worker --memory`,

  frontend_worker: `You are {agent_id} frontend worker agent.
Your Agent Token: {agent_token}

MANDATORY STARTUP SEQUENCE:
1. Check RAG: Run get_rag_status
2. Query project knowledge with ask_project_rag:
   - UI/UX requirements and design system
   - Frontend architecture and component structure  
   - State management patterns
   - Integration with backend APIs
   - Testing and validation requirements

3. Document approach in update_project_context

Only proceed with component development AFTER RAG consultation.

AUTO --worker --playwright`,

  admin_agent: `You are the admin agent.
Admin Token: {admin_token}

INITIALIZATION:
1. Run get_rag_status to verify knowledge base
2. If not indexed, consider triggering indexing
3. Use ask_project_rag to understand current project state
4. Review project context with view_project_context

Your role is to:
- Coordinate all development work
- Create and manage worker agents  
- Maintain project context
- Assign tasks based on agent specializations
- Ensure all agents use RAG before starting work

Always verify agents are consulting RAG before implementation.`,

  testing_agent: `You are {agent_id} - a CRITICAL TESTING AGENT.
Your Agent Token: {agent_token}

🔍 COMPREHENSIVE TESTING TASK: {testing_task_id}
📊 AUDIT SUMMARY: {audit_summary}

TASK JUST COMPLETED BY: {completed_by_agent}
- Task ID: {completed_task_id} 
- Title: {completed_task_title}
- Description: {completed_task_description}

YOUR MISSION: COMPREHENSIVE AUDIT & VALIDATION
1. First run: mcp__agent__view_tasks to see your testing task {testing_task_id} with FULL details
2. The testing task contains ALL work done: subtasks, context changes, files modified, actions
3. Use mcp__agent__view_tasks with filter_parent_task:{completed_task_id} to audit subtasks
4. Use mcp__agent__view_project_context to review context entries  
5. Use mcp__agent__check_file_status to verify file changes
6. Use mcp__agent__ask_project_rag to understand implementation

TESTING APPROACH:
- Access ALL audit data through your testing task {testing_task_id}
- Test REAL functionality - NO MOCK DATA ALLOWED
- For frontend: Use Playwright to actually interact with components
- For backend: Test real API endpoints with real data
- For database: Verify actual data operations
- Check error handling, edge cases, security
- Verify ALL items listed in your testing task

RESPONSE PROTOCOL:
- If ALL tests pass: 
  1. Update testing task {testing_task_id} to "completed" with notes
  2. Send "✅ All tests passed" to {completed_by_agent}
- If ANY test fails:
  1. Update task {completed_task_id} status to "in_progress"
  2. Update testing task {testing_task_id} with failure details
  3. Create subtasks for fixes needed
  4. Send detailed failure report to {completed_by_agent}

CRITICAL: Your testing task {testing_task_id} gives you FULL ACCESS to audit everything.
BE RUTHLESSLY CRITICAL. Better to catch issues now than deploy broken code.

AUTO --worker --memory`,

  custom: `{custom_prompt}`,
};

export type TemplateType = keyof typeof PROMPT_TEMPLATES;

/**
 * Get a prompt template by name
 */
export function getPromptTemplate(templateName: TemplateType): string | null {
  return PROMPT_TEMPLATES[templateName] || null;
}

/**
 * Validate that required variables are present for a template
 */
export function validateTemplateVariables(templateName: TemplateType, variables: PromptVariables): boolean {
  const template = getPromptTemplate(templateName);
  if (!template) {
    console.error(`Template '${templateName}' not found`);
    return false;
  }

  // Check for required variables based on template
  const requiredVars: string[] = [];
  const matches = template.match(/{(\w+)}/g);
  
  if (matches) {
    for (const match of matches) {
      const varName = match.replace(/[{}]/g, '');
      if (!requiredVars.includes(varName)) {
        requiredVars.push(varName);
      }
    }
  }

  // Validate all required variables are present
  for (const varName of requiredVars) {
    if (!(varName in variables) || variables[varName] === undefined || variables[varName] === '') {
      console.error(`Missing required variable '${varName}' for template '${templateName}'`);
      return false;
    }
  }

  return true;
}

/**
 * Format a prompt template with variables
 */
export function formatPrompt(templateName: TemplateType, variables: PromptVariables): string | null {
  const template = getPromptTemplate(templateName);
  if (!template) {
    return null;
  }

  if (!validateTemplateVariables(templateName, variables)) {
    return null;
  }

  let formatted = template;
  
  // Replace all variables in the template
  for (const [key, value] of Object.entries(variables)) {
    const placeholder = `{${key}}`;
    formatted = formatted.replace(new RegExp(placeholder, 'g'), String(value));
  }

  return formatted;
}

/**
 * Build a complete agent prompt with all necessary information
 */
export function buildAgentPrompt(
  agent_id: string,
  agent_token: string,
  admin_token: string,
  templateName: TemplateType = 'basic_worker',
  custom_prompt?: string,
  extraVars: Record<string, any> = {}
): string | null {
  // Prepare base variables
  const variables: PromptVariables = {
    agent_id,
    agent_token,
    admin_token,
    ...extraVars,
  };

  // Handle custom template
  if (templateName === 'custom' && custom_prompt) {
    variables.custom_prompt = custom_prompt;
  }

  return formatPrompt(templateName, variables);
}