// Prompt Book - Centralized collection of Agent-MCP prompts and workflows

export interface PromptTemplate {
  id: string
  title: string
  description: string
  category: string
  template: string
  variables: Array<{
    name: string
    description: string
    placeholder: string
    required: boolean
  }>
  usage: string
  examples?: string[]
  tags: string[]
}

export interface PromptCategory {
  id: string
  name: string
  description: string
  icon: string
}

export const promptCategories: PromptCategory[] = [
  {
    id: 'initialization',
    name: 'Agent Initialization',
    description: 'Prompts for setting up admin and worker agents',
    icon: 'UserPlus'
  },
  {
    id: 'task-management',
    name: 'Task Management',
    description: 'Prompts for creating, assigning, and managing tasks',
    icon: 'CheckSquare'
  },
  {
    id: 'context-management',
    name: 'Context Management',
    description: 'Prompts for managing project context and memory',
    icon: 'Database'
  },
  {
    id: 'debugging',
    name: 'Debugging & Analysis',
    description: 'Prompts for troubleshooting and system analysis',
    icon: 'Bug'
  },
  {
    id: 'coordination',
    name: 'Agent Coordination',
    description: 'Prompts for multi-agent coordination and communication',
    icon: 'Users'
  }
]

export const promptTemplates: PromptTemplate[] = [
  // INITIALIZATION PROMPTS
  {
    id: 'admin-init',
    title: 'Admin Agent Initialization',
    description: 'Initialize an admin agent with authentication token and context setup',
    category: 'initialization',
    template: `Initialize as an admin agent with this token: {{ADMIN_TOKEN}}
Please add the MCD.md file to the project context. Don't summarize it.`,
    variables: [
      {
        name: 'ADMIN_TOKEN',
        description: 'The admin authentication token from the MCP database',
        placeholder: 'admin_token_here',
        required: true
      }
    ],
    usage: 'Use this prompt to set up the main admin agent that will coordinate other agents and manage the project.',
    examples: [
      'Initialize as an admin agent with this token: abc123def456\nPlease add the MCD.md file to the project context. Don\'t summarize it.'
    ],
    tags: ['admin', 'initialization', 'setup', 'auth']
  },
  {
    id: 'worker-init',
    title: 'Worker Agent Initialization',
    description: 'Initialize a worker agent with specific role and autonomous behavior',
    category: 'initialization',
    template: `You are {{AGENT_ID}} agent, your Worker Token: "{{WORKER_TOKEN}}"

Look at your tasks and ask the project RAG agent at least 5-7 questions to understand what you need to do. I want you to critically think when asking a question, then criticize yourself before asking that question. How you criticize yourself is by proposing an idea, criticizing it, and based on that criticism you pull through with that idea.

AUTO --worker --memory`,
    variables: [
      {
        name: 'AGENT_ID',
        description: 'Unique identifier for the worker agent (e.g., frontend-worker, backend-worker)',
        placeholder: 'frontend-worker',
        required: true
      },
      {
        name: 'WORKER_TOKEN',
        description: 'The specific worker token provided by the admin agent',
        placeholder: 'worker_token_here',
        required: true
      }
    ],
    usage: 'Use this prompt in a new AI assistant window to initialize a worker agent that will autonomously work on assigned tasks.',
    examples: [
      'You are frontend-worker agent, your Worker Token: "xyz789abc123"\n\nLook at your tasks and ask the project RAG agent at least 5-7 questions...'
    ],
    tags: ['worker', 'initialization', 'autonomous', 'tasks']
  },
  {
    id: 'worker-init-legacy',
    title: 'Worker Agent Initialization (Legacy)',
    description: 'Legacy worker initialization format using admin token',
    category: 'initialization',
    template: `You are {{AGENT_ID}} agent, your Admin Token: "{{ADMIN_TOKEN}}"

Look at your tasks and ask the project RAG agent at least 5-7 questions to understand what you need to do. I want you to critically think when asking a question, then criticize yourself before asking that question. How you criticize yourself is by proposing an idea, criticizing it, and based on that criticism you pull through with that idea.

AUTO --worker --memory`,
    variables: [
      {
        name: 'AGENT_ID',
        description: 'Unique identifier for the worker agent',
        placeholder: 'worker-id',
        required: true
      },
      {
        name: 'ADMIN_TOKEN',
        description: 'The admin token (legacy format)',
        placeholder: 'admin-token',
        required: true
      }
    ],
    usage: 'Legacy format for worker initialization. Use the newer worker-init template when possible.',
    tags: ['worker', 'initialization', 'legacy', 'deprecated']
  },

  // TASK MANAGEMENT PROMPTS
  {
    id: 'create-worker',
    title: 'Create Worker Agent',
    description: 'Request admin agent to create a new worker agent for specific tasks',
    category: 'task-management',
    template: `Create a worker agent with ID "{{AGENT_ID}}" to {{TASK_DESCRIPTION}}.`,
    variables: [
      {
        name: 'AGENT_ID',
        description: 'Unique identifier for the new worker agent',
        placeholder: 'frontend-worker',
        required: true
      },
      {
        name: 'TASK_DESCRIPTION',
        description: 'Brief description of what the worker should accomplish',
        placeholder: 'implement the login page',
        required: true
      }
    ],
    usage: 'Tell this to your admin agent to create a new specialized worker for specific tasks.',
    examples: [
      'Create a worker agent with ID "frontend-worker" to implement the login page.',
      'Create a worker agent with ID "api-worker" to build the REST API endpoints.',
      'Create a worker agent with ID "database-worker" to design and implement the database schema.'
    ],
    tags: ['admin', 'worker-creation', 'task-assignment']
  },
  {
    id: 'assign-task',
    title: 'Assign Task to Agent',
    description: 'Assign a specific task to an existing agent',
    category: 'task-management',
    template: `Assign the following task to {{AGENT_ID}}:

Title: {{TASK_TITLE}}
Description: {{TASK_DESCRIPTION}}
Priority: {{PRIORITY}}

{{ADDITIONAL_CONTEXT}}`,
    variables: [
      {
        name: 'AGENT_ID',
        description: 'ID of the agent to assign the task to',
        placeholder: 'frontend-worker',
        required: true
      },
      {
        name: 'TASK_TITLE',
        description: 'Brief title for the task',
        placeholder: 'Implement user authentication',
        required: true
      },
      {
        name: 'TASK_DESCRIPTION',
        description: 'Detailed description of what needs to be done',
        placeholder: 'Create login form with validation and JWT token handling',
        required: true
      },
      {
        name: 'PRIORITY',
        description: 'Task priority level',
        placeholder: 'high',
        required: false
      },
      {
        name: 'ADDITIONAL_CONTEXT',
        description: 'Any additional context or requirements',
        placeholder: 'Use React hooks and follow existing component patterns',
        required: false
      }
    ],
    usage: 'Use this to assign specific tasks to agents through the admin agent.',
    tags: ['task-assignment', 'admin', 'project-management']
  },

  // CONTEXT MANAGEMENT PROMPTS
  {
    id: 'add-context',
    title: 'Add Project Context',
    description: 'Add important information to the project context database',
    category: 'context-management',
    template: `Please add the {{FILE_NAME}} file to the project context. {{INSTRUCTION}}`,
    variables: [
      {
        name: 'FILE_NAME',
        description: 'Name of the file to add to context',
        placeholder: 'MCD.md',
        required: true
      },
      {
        name: 'INSTRUCTION',
        description: 'Special instructions for how to process the file',
        placeholder: "Don't summarize it.",
        required: false
      }
    ],
    usage: 'Use this to add important project files to the shared context database.',
    examples: [
      'Please add the MCD.md file to the project context. Don\'t summarize it.',
      'Please add the API-specification.md file to the project context.',
      'Please add the database-schema.sql file to the project context. Include all table structures.'
    ],
    tags: ['context', 'documentation', 'knowledge-management']
  },
  {
    id: 'rag-query',
    title: 'Query Project RAG',
    description: 'Ask questions about the project using the RAG system',
    category: 'context-management',
    template: `Ask the project RAG: "{{QUESTION}}"`,
    variables: [
      {
        name: 'QUESTION',
        description: 'Question to ask the RAG system about the project',
        placeholder: 'What is the database schema for user authentication?',
        required: true
      }
    ],
    usage: 'Use this format to query the RAG system for project-specific information.',
    examples: [
      'Ask the project RAG: "What is the authentication flow for the application?"',
      'Ask the project RAG: "What components have already been implemented?"',
      'Ask the project RAG: "What are the API endpoints for user management?"'
    ],
    tags: ['rag', 'query', 'knowledge-retrieval']
  },

  // DEBUGGING PROMPTS
  {
    id: 'debug-agent-status',
    title: 'Debug Agent Status',
    description: 'Check the status and health of agents in the system',
    category: 'debugging',
    template: `Please check the status of all agents and provide a summary of:
1. Active agents and their current tasks
2. Any failed or stuck agents
3. Task completion status
4. System health overview

{{SPECIFIC_CONCERNS}}`,
    variables: [
      {
        name: 'SPECIFIC_CONCERNS',
        description: 'Any specific issues or concerns to investigate',
        placeholder: 'Focus on why the frontend-worker seems to be stuck',
        required: false
      }
    ],
    usage: 'Use this with the admin agent to get a comprehensive system status report.',
    tags: ['debugging', 'status', 'health-check', 'admin']
  },
  {
    id: 'debug-task-flow',
    title: 'Debug Task Flow',
    description: 'Analyze task dependencies and execution flow',
    category: 'debugging',
    template: `Analyze the task flow for {{TASK_OR_FEATURE}} and identify:
1. Task dependencies and order
2. Any blocking issues
3. Agent assignments and capabilities
4. Estimated completion timeline

Please provide recommendations for optimization.`,
    variables: [
      {
        name: 'TASK_OR_FEATURE',
        description: 'Specific task or feature to analyze',
        placeholder: 'user authentication system',
        required: true
      }
    ],
    usage: 'Use this to analyze complex task dependencies and identify bottlenecks.',
    tags: ['debugging', 'task-analysis', 'workflow', 'optimization']
  },

  // COORDINATION PROMPTS
  {
    id: 'coordinate-agents',
    title: 'Coordinate Multiple Agents',
    description: 'Coordinate work between multiple agents on related tasks',
    category: 'coordination',
    template: `Coordinate the following agents to work on {{PROJECT_PHASE}}:

Agents involved:
{{AGENT_LIST}}

Requirements:
- {{REQUIREMENT_1}}
- {{REQUIREMENT_2}}
- {{REQUIREMENT_3}}

Please ensure proper communication and dependency management between agents.`,
    variables: [
      {
        name: 'PROJECT_PHASE',
        description: 'The project phase or feature being worked on',
        placeholder: 'user authentication implementation',
        required: true
      },
      {
        name: 'AGENT_LIST',
        description: 'List of agents and their roles',
        placeholder: '- frontend-worker: UI components\n- backend-worker: API endpoints\n- database-worker: schema design',
        required: true
      },
      {
        name: 'REQUIREMENT_1',
        description: 'First coordination requirement',
        placeholder: 'Frontend and backend must agree on API contract',
        required: false
      },
      {
        name: 'REQUIREMENT_2',
        description: 'Second coordination requirement',
        placeholder: 'Database schema must be finalized before API implementation',
        required: false
      },
      {
        name: 'REQUIREMENT_3',
        description: 'Third coordination requirement',
        placeholder: 'All components must follow the established design system',
        required: false
      }
    ],
    usage: 'Use this with the admin agent to coordinate complex multi-agent workflows.',
    tags: ['coordination', 'multi-agent', 'project-management', 'admin']
  },
  {
    id: 'handoff-task',
    title: 'Task Handoff Between Agents',
    description: 'Transfer a task from one agent to another with context',
    category: 'coordination',
    template: `Transfer task "{{TASK_TITLE}}" from {{FROM_AGENT}} to {{TO_AGENT}}.

Current Status:
{{CURRENT_STATUS}}

Handoff Notes:
{{HANDOFF_NOTES}}

Next Steps:
{{NEXT_STEPS}}`,
    variables: [
      {
        name: 'TASK_TITLE',
        description: 'Title of the task being transferred',
        placeholder: 'User Profile Component',
        required: true
      },
      {
        name: 'FROM_AGENT',
        description: 'Agent currently working on the task',
        placeholder: 'frontend-worker-1',
        required: true
      },
      {
        name: 'TO_AGENT',
        description: 'Agent who will take over the task',
        placeholder: 'frontend-worker-2',
        required: true
      },
      {
        name: 'CURRENT_STATUS',
        description: 'Current state of the task',
        placeholder: 'Basic component structure completed, needs styling and validation',
        required: true
      },
      {
        name: 'HANDOFF_NOTES',
        description: 'Important context for the new agent',
        placeholder: 'Component uses React Hook Form for validation, follow existing pattern in LoginForm',
        required: true
      },
      {
        name: 'NEXT_STEPS',
        description: 'What the new agent should focus on',
        placeholder: '1. Add form validation\n2. Implement responsive design\n3. Add unit tests',
        required: true
      }
    ],
    usage: 'Use this to properly transfer tasks between agents with full context preservation.',
    tags: ['handoff', 'task-transfer', 'coordination', 'context-preservation']
  }
]

// Helper functions for working with prompts
export function getPromptsByCategory(categoryId: string): PromptTemplate[] {
  return promptTemplates.filter(prompt => prompt.category === categoryId)
}

export function searchPrompts(query: string): PromptTemplate[] {
  const lowercaseQuery = query.toLowerCase()
  return promptTemplates.filter(prompt =>
    prompt.title.toLowerCase().includes(lowercaseQuery) ||
    prompt.description.toLowerCase().includes(lowercaseQuery) ||
    prompt.tags.some(tag => tag.toLowerCase().includes(lowercaseQuery)) ||
    prompt.template.toLowerCase().includes(lowercaseQuery)
  )
}

export function getPromptById(id: string): PromptTemplate | undefined {
  return promptTemplates.find(prompt => prompt.id === id)
}

export function fillPromptTemplate(template: string, variables: Record<string, string>): string {
  let filled = template
  Object.entries(variables).forEach(([key, value]) => {
    const regex = new RegExp(`{{${key}}}`, 'g')
    filled = filled.replace(regex, value)
  })
  return filled
}

export function getRequiredVariables(prompt: PromptTemplate): string[] {
  return prompt.variables.filter(v => v.required).map(v => v.name)
}

export function validatePromptVariables(prompt: PromptTemplate, variables: Record<string, string>): string[] {
  const errors: string[] = []
  const required = getRequiredVariables(prompt)
  
  required.forEach(varName => {
    if (!variables[varName] || variables[varName].trim() === '') {
      errors.push(`Required variable "${varName}" is missing or empty`)
    }
  })
  
  return errors
}