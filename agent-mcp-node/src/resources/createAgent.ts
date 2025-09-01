// MCP Resource for Creating Agents via @ mentions
// Provides a convenient way to create background agents

import { MCP_DEBUG } from '../core/config.js';

export interface CreateAgentResource {
  uri: string;
  name: string;
  description: string;
  mimeType: string;
  annotations?: any;
}

export interface CreateAgentResourceContent {
  uri: string;
  mimeType: string;
  text: string;
}

/**
 * Get create agent resources - different templates for different agent types
 */
export async function getCreateAgentResources(): Promise<CreateAgentResource[]> {
  const resources: CreateAgentResource[] = [];
  
  // Three focused agent creation templates
  const templates = [
    {
      name: 'create-agent',
      description: '\x1b[1;38;2;255;165;0m📋 Create normal agent (with tasks)\x1b[0m',
      template: 'normal'
    },
    {
      name: 'create-background',
      description: '\x1b[1;95m🤖 Create background agent (autonomous)\x1b[0m',
      template: 'background'
    },
    {
      name: 'create-monitor',
      description: '\x1b[1;93m👁️ Create monitor agent (rule-based)\x1b[0m',
      template: 'monitor'
    }
  ];
  
  templates.forEach(template => {
    resources.push({
      uri: `create://${template.template}`,
      name: `\x1b[1;92m@${template.name}\x1b[0m`,
      description: template.description,
      mimeType: 'text/markdown',
      annotations: {
        type: 'create-agent',
        template: template.template,
        category: 'automation'
      }
    });
  });
  
  return resources;
}

/**
 * Get create agent resource content - returns instructions and examples
 */
export async function getCreateAgentResourceContent(uri: string): Promise<CreateAgentResourceContent | null> {
  const template = uri.replace('create://', '');
  
  let content = '';
  
  switch (template) {
    case 'normal':
      content = `# 📋 Create Normal Agent (Task-Based)

## Purpose:
Create an agent that works through assigned tasks hierarchically.

## When to use:
- You have specific tasks to complete
- Tasks have dependencies or order
- You want progress tracking
- Work can be broken into subtasks

## Examples:
"Create an agent to refactor the authentication module"
"Create an agent to implement the new feature X with tests"
"Create an agent to migrate database schema"

## Command:
\`\`\`javascript
assign_task({
  token: "@admin",
  agent_token: "@agent-name", 
  task_title: "Your task",
  task_description: "Details..."
})
\`\`\`

**Note:** Normal agents require task assignment!
`;
      break;
      
    case 'background':
      content = `# 🤖 Create Background Agent (Autonomous)

## Purpose:
Create an autonomous agent that runs continuously without tasks.

## When to use:
- Continuous monitoring needed
- No specific task structure
- General assistance/support
- Long-running services

## Examples:
"Monitor the codebase and suggest improvements"
"Keep documentation up to date"
"Run periodic health checks"
"Answer questions about the project"

## Command:
\`\`\`javascript
create_background_agent({
  agent_id: "agent-name",
  objectives: ["objective 1", "objective 2"]
})
\`\`\`

**Note:** No admin token needed!
`;
      break;
      
    case 'monitor':
      content = `# 👁️ Create Monitor Agent (Rule-Based)

## Purpose:
Create an agent that monitors based on specific rules and conditions.

## When to use:
- Watching for specific events
- Rule-based triggers needed
- Alert on conditions
- Compliance monitoring

## Rules Format:
- **IF** file changes **THEN** run tests
- **IF** error in logs **THEN** alert admin
- **IF** CPU > 80% **THEN** scale up
- **IF** PR opened **THEN** run checks

## Examples:
"Monitor logs for ERROR and alert immediately"
"Watch src/ and run build when .ts files change"
"Monitor API response times and alert if > 500ms"

## Command:
\`\`\`javascript
create_background_agent({
  agent_id: "monitor-name",
  mode: "monitoring",
  objectives: [
    "IF condition THEN action",
    "Monitor X for Y"
  ]
})
\`\`\`
`;
      break;
      
      
    default:
      return null;
  }
  
  return {
    uri,
    mimeType: 'text/markdown',
    text: content
  };
}

if (MCP_DEBUG) {
  console.log('✅ Create Agent resources module loaded');
}