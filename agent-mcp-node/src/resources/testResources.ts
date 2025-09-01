// Test Resources to match Claude Code patterns
// Trying to reverse-engineer how Claude Code determines resource colors

export interface TestResource {
  uri: string;
  name: string;
  description: string;
  mimeType: string;
  annotations?: any; // Allow any metadata
}

/**
 * Create test resources that might trigger Claude Code's coloring system
 */
export async function getTestResources(): Promise<TestResource[]> {
  return [
    // Method 1: Add ANSI codes to name like test 7
    {
      uri: 'agent-statusline-setup',
      name: '@test-resource-1-statusline',
      description: '\x1b[1;38;2;255;165;0mMethod 1: Claude Code orange like agent status\x1b[0m',
      mimeType: 'text/plain'
    },
    // Method 2: Add ANSI codes to name 
    {
      uri: 'error://test-resource-2',
      name: '@test-resource-2-error',
      description: '\x1b[1;94mMethod 2: Bold bright blue ANSI codes\x1b[0m',
      mimeType: 'text/plain'
    },
    // Method 3: Add ANSI codes to name
    {
      uri: 'warning://test-resource-3',
      name: '@test-resource-3-warning',
      description: '\x1b[1;93mMethod 3: Bold bright yellow terminal colors\x1b[0m',
      mimeType: 'text/plain'
    },
    // Method 4: Copy exact phrase but different color
    {
      uri: 'file:///test/resource.ts',
      name: '@test-resource-4 (cyan)',
      description: '\x1b[1;96mMethod 4: Bold bright cyan terminal codes\x1b[0m',
      mimeType: 'text/plain'
    },
    // Method 5: Try without "bright"
    {
      uri: 'http://localhost:3000/api/500',
      name: '@test-resource-5 (magenta)',
      description: '\x1b[1;95mMethod 5: Bold bright magenta terminal codes\x1b[0m',
      mimeType: 'text/plain'
    },
    // Method 6: Try "escape codes" phrase
    {
      uri: 'git://modified/test.js',
      name: '@test-resource-6-git',
      description: 'Method 6: Git status pattern',
      mimeType: 'text/plain'
    },
    // Method 7: BASELINE - Keep this working! 
    {
      uri: 'success://test-resource-7',
      name: '@test-resource-7-success',
      description: '\x1b[1;92mMethod 7: Bold bright green terminal codes (BASELINE)\x1b[0m',
      mimeType: 'text/plain'
    },
    // Method 8: Try different "bright" colors
    {
      uri: 'test://🔴resource/8',
      name: '@test-resource-8-red',
      description: 'Method 8: MimeType experiment',
      mimeType: 'text/x-red'
    },
    // Method 9: Try "codes" keyword
    {
      uri: 'test://404/not-found',
      name: '@test-resource-9',
      description: 'Method 9: Color codes (bright magenta)',
      mimeType: 'text/plain'
    },
    // Method 10: Try exact copy of 7 but red
    {
      uri: 'terminal://ansi/color/red',
      name: '@test-resource-10',
      description: 'Method 10: Terminal color codes (bright red)',
      mimeType: 'text/plain'
    }
  ];
}

/**
 * Get test resource content
 */
export async function getTestResourceContent(uri: string): Promise<{ uri: string; mimeType: string; text: string }> {
  return {
    uri,
    mimeType: 'text/plain',
    text: `Test resource content for: ${uri}\n\nThis is a test resource created to understand how Claude Code applies colors to MCP resources.`
  };
}