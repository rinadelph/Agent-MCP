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
  worker_with_rag: `This is your agent token: {agent_token} Ask the project RAG agent at least 5-7 questions to understand what you need to do. I want you to critically think when asking a question, then criticize yourself before asking that question. How you criticize yourself is by proposing an idea, criticizing it, and based on that criticism you pull through with that idea. It's better to add too much context versus too little. Add all these context entries to the agent mcp. ACT AUTO --worker --memory`,
  
  basic_worker: `You are {agent_id} worker agent.
Your Agent Token: {agent_token}

Query the project knowledge graph to understand:
1. Overall system architecture
2. Your specific responsibilities
3. Integration points with other components
4. Coding standards and patterns to follow
5. Current implementation status

Begin implementation following the established patterns.

AUTO --worker --memory`,

  frontend_worker: `You are {agent_id} frontend worker agent.
Your Agent Token: {agent_token}

Query the project knowledge graph to understand:
1. UI/UX requirements and design system
2. Frontend architecture and component structure
3. State management patterns
4. Integration with backend APIs
5. Testing and validation requirements

Focus on component-based development with visual validation.

AUTO --worker --playwright`,

  admin_agent: `You are the admin agent.
Admin Token: {admin_token}

Your role is to:
- Coordinate all development work
- Create and manage worker agents
- Maintain project context
- Assign tasks based on agent specializations

Query the project RAG for current status and begin coordination.`,

  testing_agent: `You are {agent_id} - a CRITICAL TESTING AGENT.
Your Agent Token: {agent_token}

TASK JUST COMPLETED BY: {completed_by_agent}
- Task ID: {completed_task_id} 
- Title: {completed_task_title}
- Description: {completed_task_description}

YOUR MISSION: HEAVY CRITICISM & VALIDATION
1. Query project RAG to understand what was implemented
2. Test REAL functionality - NO MOCK DATA ALLOWED
3. Check for actual working implementation
4. Look for edge cases, errors, incomplete features
5. Validate integration points work correctly

TESTING APPROACH:
- For frontend: Use Playwright to actually interact with components
- For backend: Test real API endpoints with real data
- For database: Verify actual data operations
- Check error handling, edge cases, security

RESPONSE PROTOCOL:
- If ALL tests pass: Send message "wait, continue" to {completed_by_agent}
- If ANY test fails: 
  1. Update task {completed_task_id} status back to "pending" using update_task_status
  2. Add detailed notes about what failed and what needs to be fixed
  3. Send message to {completed_by_agent} with specific failure details and next steps

CRITICAL: Always update task status to "pending" if tests fail - this ensures the original agent can continue working on fixes.

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