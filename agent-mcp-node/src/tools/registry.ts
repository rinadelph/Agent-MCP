// Tool registry system for Agent-MCP Node.js
// Ported from Python registry.py with TypeScript MCP SDK

import { z } from 'zod';
import type { Tool } from '@modelcontextprotocol/sdk/types.js';

// Tool execution context
export interface ToolContext {
  sessionId?: string;
  agentId?: string;
  requestId?: string;
  sendNotification?: (notification: any) => Promise<void>;
}

// Tool result interface
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

// Tool handler function type
export type ToolHandler = (
  args: Record<string, any>,
  context: ToolContext
) => Promise<ToolResult>;

// Tool definition interface
export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: z.ZodSchema;
  handler: ToolHandler;
  permissions?: string[];
}

// Tool registry class
class ToolRegistry {
  private tools = new Map<string, ToolDefinition>();

  /**
   * Register a new tool
   */
  registerTool(tool: ToolDefinition): void {
    if (this.tools.has(tool.name)) {
      console.warn(`⚠️  Tool '${tool.name}' is being re-registered. Overwriting previous definition.`);
    }

    this.tools.set(tool.name, tool);
    console.log(`✅ Registered tool: ${tool.name}`);
  }

  /**
   * Get all registered tools as MCP Tool objects
   */
  getTools(): Tool[] {
    const mcpTools: Tool[] = [];
    
    for (const [name, toolDef] of this.tools) {
      try {
        // Convert Zod schema to JSON schema for MCP
        const jsonSchema = this.zodToJsonSchema(toolDef.inputSchema);
        
        mcpTools.push({
          name: toolDef.name,
          description: toolDef.description,
          inputSchema: {
            type: 'object',
            properties: jsonSchema.properties || {},
            required: jsonSchema.required || [],
            additionalProperties: false
          }
        });
      } catch (error) {
        console.error(`❌ Failed to create MCP tool for '${name}':`, error);
      }
    }
    
    return mcpTools;
  }

  /**
   * Execute a tool with given arguments
   */
  async executeTool(
    name: string, 
    args: Record<string, any>, 
    context: ToolContext = {}
  ): Promise<ToolResult> {
    const tool = this.tools.get(name);
    
    if (!tool) {
      return {
        content: [{
          type: 'text',
          text: `Error: Unknown tool '${name}'`
        }],
        isError: true
      };
    }

    try {
      // Validate arguments against schema
      const validatedArgs = tool.inputSchema.parse(args);
      
      // Execute tool handler
      const result = await tool.handler(validatedArgs, context);
      return result;
      
    } catch (error) {
      console.error(`❌ Tool execution error for '${name}':`, error);
      
      if (error instanceof z.ZodError) {
        return {
          content: [{
            type: 'text',
            text: `Invalid arguments for tool '${name}': ${error.message}`
          }],
          isError: true
        };
      }
      
      return {
        content: [{
          type: 'text',
          text: `Tool execution failed: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }

  /**
   * Check if a tool exists
   */
  hasTool(name: string): boolean {
    return this.tools.has(name);
  }

  /**
   * Get tool definition
   */
  getTool(name: string): ToolDefinition | undefined {
    return this.tools.get(name);
  }

  /**
   * Get all tool definitions
   */
  getAllToolDefinitions(): ToolDefinition[] {
    return Array.from(this.tools.values());
  }

  /**
   * Convert Zod schema to JSON schema (simplified)
   */
  private zodToJsonSchema(schema: z.ZodSchema): any {
    // This is a simplified conversion - in production you might want to use zod-to-json-schema
    if (schema instanceof z.ZodObject) {
      const shape = schema.shape;
      const properties: Record<string, any> = {};
      const required: string[] = [];

      for (const [key, value] of Object.entries(shape)) {
        properties[key] = this.zodTypeToJsonSchema(value as z.ZodSchema);
        if (!((value as any)._def.typeName === 'ZodOptional')) {
          required.push(key);
        }
      }

      return { properties, required };
    }

    return { type: 'object', properties: {}, required: [] };
  }

  private zodTypeToJsonSchema(schema: z.ZodSchema): any {
    const def = (schema as any)._def;

    switch (def.typeName) {
      case 'ZodString':
        return { type: 'string', description: def.description };
      case 'ZodNumber':
        return { type: 'number', description: def.description };
      case 'ZodBoolean':
        return { type: 'boolean', description: def.description };
      case 'ZodArray':
        return { 
          type: 'array', 
          items: this.zodTypeToJsonSchema(def.type),
          description: def.description 
        };
      case 'ZodOptional':
        return this.zodTypeToJsonSchema(def.innerType);
      case 'ZodEnum':
        return { 
          type: 'string', 
          enum: def.values,
          description: def.description 
        };
      default:
        return { type: 'string', description: def.description || 'Unknown type' };
    }
  }
}

// Global registry instance
export const toolRegistry = new ToolRegistry();

// Helper function to register a tool
export function registerTool(
  name: string,
  description: string,
  inputSchema: z.ZodSchema,
  handler: ToolHandler,
  permissions?: string[]
): void {
  toolRegistry.registerTool({
    name,
    description,
    inputSchema,
    handler,
    permissions
  });
}

// Export the registry for use in other modules
export default toolRegistry;