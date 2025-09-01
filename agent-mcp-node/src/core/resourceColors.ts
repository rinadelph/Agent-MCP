// Resource Color Utilities
// Provides both ANSI escape codes and semantic color metadata for MCP resources

export interface ColorMetadata {
  color: string;
  ansiCode: string;
  priority: 'low' | 'normal' | 'high' | 'critical';
}

export const COLOR_MAPPING: Record<string, ColorMetadata> = {
  red: {
    color: 'red',
    ansiCode: '\x1b[91m', // Bright red
    priority: 'critical'
  },
  green: {
    color: 'green', 
    ansiCode: '\x1b[92m', // Bright green
    priority: 'normal'
  },
  yellow: {
    color: 'yellow',
    ansiCode: '\x1b[93m', // Bright yellow
    priority: 'high'
  },
  blue: {
    color: 'blue',
    ansiCode: '\x1b[94m', // Bright blue
    priority: 'normal'
  },
  magenta: {
    color: 'magenta',
    ansiCode: '\x1b[95m', // Bright magenta
    priority: 'normal'
  },
  cyan: {
    color: 'cyan',
    ansiCode: '\x1b[96m', // Bright cyan
    priority: 'normal'
  },
  white: {
    color: 'white',
    ansiCode: '\x1b[97m', // Bright white
    priority: 'low'
  },
  orange: {
    color: 'orange',
    ansiCode: '\x1b[33m', // Orange (regular yellow)
    priority: 'high'
  },
  gray: {
    color: 'gray',
    ansiCode: '\x1b[37m', // Light gray
    priority: 'low'
  }
};

export const RESET_CODE = '\x1b[0m';

/**
 * Create a resource name with both ANSI color codes and semantic metadata
 */
export function createColoredResourceName(baseName: string, colorKey: string, options: {
  useAnsi?: boolean;
  prefix?: string;
} = {}): string {
  const { useAnsi = true, prefix = '@' } = options;
  const colorData = COLOR_MAPPING[colorKey] || COLOR_MAPPING.white;
  
  if (useAnsi && colorData) {
    return `${colorData.ansiCode}${prefix}${baseName}${RESET_CODE}`;
  } else {
    return `${prefix}${baseName}`;
  }
}

/**
 * Get semantic color metadata for a resource
 */
export function getColorMetadata(colorKey: string): ColorMetadata {
  return COLOR_MAPPING[colorKey] || COLOR_MAPPING.white!;
}

/**
 * Enhanced resource interface with hybrid coloring support
 */
export interface ColoredResource {
  uri: string;
  name: string;
  description: string;
  mimeType: string;
  annotations?: {
    color?: string;
    type?: string;
    status?: string;
    priority?: string;
    // Additional metadata for Claude Code
    category?: string;
    lastUsed?: string;
    importance?: 'low' | 'normal' | 'high' | 'critical';
  };
}

/**
 * Create a hybrid colored resource with both ANSI and semantic support
 */
export function createColoredResource(
  uri: string,
  baseName: string,
  colorKey: string,
  type: string,
  status: string,
  description: string = '',
  options: {
    useAnsi?: boolean;
    prefix?: string;
    mimeType?: string;
    category?: string;
  } = {}
): ColoredResource {
  const {
    useAnsi = false, // Default to semantic-only for Claude Code compatibility
    prefix = '@',
    mimeType = 'application/json',
    category = type
  } = options;

  const colorData = getColorMetadata(colorKey);
  
  return {
    uri,
    name: createColoredResourceName(baseName, colorKey, { useAnsi, prefix }),
    description: description || `${type} (${status})`,
    mimeType,
    annotations: {
      color: colorData.color,
      type,
      status,
      priority: colorData.priority,
      category,
      importance: colorData.priority as 'low' | 'normal' | 'high' | 'critical'
    }
  };
}

/**
 * Test function to demonstrate hybrid coloring
 */
export function testColoredResources(): void {
  console.log('🎨 Testing Resource Colors:\n');
  
  const testResources = [
    { name: 'admin', color: 'red', type: 'token', status: 'critical' },
    { name: 'agent-01', color: 'magenta', type: 'agent', status: 'active' },
    { name: 'tmux-session', color: 'green', type: 'tmux', status: 'attached' },
    { name: 'monitor', color: 'yellow', type: 'token', status: 'monitoring' },
    { name: 'service-api', color: 'cyan', type: 'service', status: 'running' }
  ];

  console.log('ANSI Colors (for terminals):');
  testResources.forEach(resource => {
    const colored = createColoredResource(
      `${resource.type}://${resource.name}`,
      resource.name,
      resource.color,
      resource.type,
      resource.status,
      `Test ${resource.type}`,
      { useAnsi: true }
    );
    console.log(`  ${colored.name}`);
  });

  console.log('\nSemantic Colors (for Claude Code):');
  testResources.forEach(resource => {
    const colored = createColoredResource(
      `${resource.type}://${resource.name}`,
      resource.name,
      resource.color,
      resource.type,
      resource.status,
      `Test ${resource.type}`,
      { useAnsi: false }
    );
    console.log(`  ${colored.name} [${colored.annotations?.color}]`);
  });
}