// Practical TUI for Agent-MCP - No animations, focus on functionality
// Handles embedding providers, CLI selection, and tool management efficiently

import inquirer from 'inquirer';
import { 
  ToolCategories, 
  PREDEFINED_MODES, 
  DEFAULT_CONFIG,
  loadToolConfig, 
  saveToolConfig, 
  getConfigMode,
  validateToolConfig,
  getCategoryDescription
} from '../core/toolConfig.js';
import { TUIColors } from '../core/config.js';
import { 
  loadExtendedConfig, 
  saveExtendedConfig, 
  validateEmbeddingProviderConfig,
  ExtendedConfig,
  loadNamedConfigs,
  saveNamedConfig,
  loadNamedConfig,
  deleteNamedConfig,
  NamedConfig
} from '../core/extendedConfig.js';
import { isPortAvailable, findAvailablePort, getPortRecommendations } from '../core/portChecker.js';
import { 
  getCurrentEnvValues,
  setEnvVariable,
  validateApiKey,
  maskApiKey,
  MANAGED_ENV_VARS,
  EnvVariable,
  getEnvVariablesByCategory,
  reloadEnvironmentVariables
} from '../core/envManager.js';

// Available embedding providers
export const EMBEDDING_PROVIDERS = {
  openai: {
    name: 'OpenAI',
    description: 'OpenAI text-embedding-3-large (requires OPENAI_API_KEY)',
    envVar: 'OPENAI_API_KEY',
    recommended: true
  },
  ollama: {
    name: 'Ollama', 
    description: 'Local Ollama embeddings (requires Ollama running)',
    envVar: null,
    recommended: true
  },
  huggingface: {
    name: 'HuggingFace',
    description: 'HuggingFace models (API key or local transformers)',
    envVar: 'HUGGINGFACE_API_KEY',
    recommended: false
  },
  gemini: {
    name: 'Google Gemini',
    description: 'Google Gemini embeddings (requires GEMINI_API_KEY)', 
    envVar: 'GEMINI_API_KEY',
    recommended: false
  },
  localserver: {
    name: 'Local Server',
    description: 'Custom local embedding server',
    envVar: null,
    recommended: false
  }
} as const;

// Available CLI agents for background tasks
export const CLI_AGENTS = {
  claude: {
    name: 'Claude CLI',
    command: 'claude',
    description: 'Anthropic Claude (recommended, full MCP support)',
    recommended: true,
    mcpSupport: true
  },
  gemini: {
    name: 'Gemini CLI', 
    command: 'gemini',
    description: 'Google Gemini (MCP support via settings.json)',
    recommended: true,
    mcpSupport: true
  },
  llxprt: {
    name: 'LLXprt CLI',
    command: 'llxprt',
    description: 'LLXprt multi-provider client (full MCP support)',
    recommended: false,
    mcpSupport: true
  },
  swarmcode: {
    name: 'SwarmCode CLI',
    command: 'swarmcode', 
    description: 'SwarmCode multi-agent system (MCP support)',
    recommended: false,
    mcpSupport: true
  }
} as const;

function displayHeader() {
  console.clear();
  console.log(`${TUIColors.HEADER}${TUIColors.BOLD}╔══════════════════════════════════════════════════════════════╗`);
  console.log(`║                    Agent-MCP Configuration                    ║`);
  console.log(`║                     Practical Setup                          ║`);
  console.log(`╚══════════════════════════════════════════════════════════════╝${TUIColors.ENDC}`);
  console.log();
}

async function handleNamedConfigurations(): Promise<ExtendedConfig | null> {
  console.log(`${TUIColors.OKBLUE}${TUIColors.BOLD}📋 Configuration Management${TUIColors.ENDC}`);
  console.log();
  
  const namedConfigs = loadNamedConfigs();
  
  if (namedConfigs.length === 0) {
    console.log('No saved configurations found.');
    console.log();
    return null;
  }
  
  console.log('Saved Configurations:');
  namedConfigs.forEach(config => {
    const lastUsed = config.lastUsed ? 
      new Date(config.lastUsed).toLocaleDateString() : 
      'Never used';
    console.log(`  • ${TUIColors.OKGREEN}${config.name}${TUIColors.ENDC} - ${config.description}`);
    console.log(`    Created: ${new Date(config.createdAt).toLocaleDateString()}, Last used: ${lastUsed}`);
  });
  console.log();
  
  const configAction = await inquirer.prompt({
    type: 'list',
    name: 'action',
    message: 'What would you like to do?',
    choices: [
      { name: 'Load a saved configuration', value: 'load' },
      { name: 'Create new configuration', value: 'new' },
      { name: 'Delete a saved configuration', value: 'delete' }
    ]
  });
  
  if (configAction.action === 'load') {
    const configChoice = await inquirer.prompt({
      type: 'list',
      name: 'config',
      message: 'Select configuration to load:',
      choices: namedConfigs.map(config => ({
        name: `${config.name} - ${config.description}`,
        value: config.name,
        short: config.name
      }))
    });
    
    const selectedConfig = loadNamedConfig(configChoice.config);
    if (selectedConfig) {
      console.log(`${TUIColors.OKGREEN}✅ Loaded configuration: ${selectedConfig.name}${TUIColors.ENDC}`);
      return selectedConfig.config;
    }
  }
  
  if (configAction.action === 'delete') {
    const configChoice = await inquirer.prompt({
      type: 'list',
      name: 'config',
      message: 'Select configuration to delete:',
      choices: namedConfigs.map(config => ({
        name: `${config.name} - ${config.description}`,
        value: config.name,
        short: config.name
      }))
    });
    
    const confirm = await inquirer.prompt({
      type: 'confirm',
      name: 'delete',
      message: `Delete configuration '${configChoice.config}'?`,
      default: false
    });
    
    if (confirm.delete) {
      deleteNamedConfig(configChoice.config);
      console.log(`${TUIColors.OKGREEN}✅ Configuration deleted${TUIColors.ENDC}`);
    }
    
    return await handleNamedConfigurations();
  }
  
  return null;
}

async function getTabCompletion(partialPath: string): Promise<{ completion: string; suggestions: string[] }> {
  try {
    const fs = await import('fs');
    const path = await import('path');
    const os = await import('os');
    
    let searchPath = partialPath;
    let prefix = '';
    
    // Handle home directory expansion
    if (partialPath.startsWith('~')) {
      searchPath = partialPath.replace('~', os.homedir());
    }
    
    // If path doesn't exist, get parent directory and prefix
    if (!fs.existsSync(searchPath)) {
      prefix = path.basename(searchPath);
      searchPath = path.dirname(searchPath);
    }
    
    if (!fs.existsSync(searchPath)) {
      return { completion: partialPath, suggestions: [] };
    }
    
    const entries = fs.readdirSync(searchPath, { withFileTypes: true });
    const directories = entries
      .filter(entry => entry.isDirectory())
      .map(entry => entry.name)
      .filter(name => prefix ? name.toLowerCase().startsWith(prefix.toLowerCase()) : true)
      .sort();
    
    if (directories.length === 0) {
      return { completion: partialPath, suggestions: [] };
    }
    
    // If only one match, complete it
    if (directories.length === 1) {
      const completedPath = path.join(searchPath, directories[0]);
      return { 
        completion: completedPath.endsWith('/') ? completedPath : completedPath + '/', 
        suggestions: [completedPath] 
      };
    }
    
    // Multiple matches - find common prefix
    let commonPrefix = directories[0];
    for (let i = 1; i < directories.length; i++) {
      let j = 0;
      while (j < commonPrefix.length && j < directories[i].length && 
             commonPrefix[j].toLowerCase() === directories[i][j].toLowerCase()) {
        j++;
      }
      commonPrefix = commonPrefix.substring(0, j);
    }
    
    const suggestions = directories.map(dir => path.join(searchPath, dir));
    
    if (commonPrefix.length > prefix.length) {
      const completedPath = path.join(searchPath, commonPrefix);
      return { completion: completedPath, suggestions };
    }
    
    return { completion: partialPath, suggestions };
  } catch (error) {
    return { completion: partialPath, suggestions: [] };
  }
}

async function selectProjectDirectoryWithTabCompletion(): Promise<string> {
  const fs = await import('fs');
  const path = await import('path');
  const os = await import('os');
  
  console.log(`${TUIColors.DIM}💡 Type path and press TAB to complete, ENTER when done${TUIColors.ENDC}`);
  console.log(`${TUIColors.DIM}   Use '~' for home directory, Ctrl+C to cancel${TUIColors.ENDC}`);
  console.log();
  
  return new Promise((resolve, reject) => {
    let currentInput = '';
    let cursorPosition = 0;
    
    // Set raw mode to capture individual key presses
    if (process.stdin.setRawMode) {
      process.stdin.setRawMode(true);
    }
    process.stdin.resume();
    
    // Display initial prompt
    process.stdout.write('📁 Enter project directory path: ');
    
    const cleanup = () => {
      if (process.stdin.setRawMode) {
        process.stdin.setRawMode(false);
      }
      process.stdin.removeAllListeners('data');
    };
    
    process.stdin.on('data', async (key) => {
      const keyStr = key.toString();
      
      // Handle Ctrl+C
      if (key[0] === 3) {
        cleanup();
        console.log('\n');
        reject(new Error('Directory selection cancelled'));
        return;
      }
      
      // Handle Enter
      if (keyStr === '\r' || keyStr === '\n') {
        cleanup();
        console.log('\n');
        
        let finalPath = currentInput.trim();
        
        if (!finalPath) {
          reject(new Error('No path provided'));
          return;
        }
        
        // Expand home directory
        if (finalPath.startsWith('~')) {
          finalPath = finalPath.replace('~', os.homedir());
        }
        
        // Validate path
        try {
          if (!path.isAbsolute(finalPath)) {
            console.log(`${TUIColors.FAIL}❌ Path must be absolute${TUIColors.ENDC}`);
            reject(new Error('Path must be absolute'));
            return;
          }
          
          if (!fs.existsSync(finalPath)) {
            console.log(`${TUIColors.FAIL}❌ Directory does not exist: ${finalPath}${TUIColors.ENDC}`);
            reject(new Error('Directory does not exist'));
            return;
          }
          
          const stats = fs.statSync(finalPath);
          if (!stats.isDirectory()) {
            console.log(`${TUIColors.FAIL}❌ Path is not a directory: ${finalPath}${TUIColors.ENDC}`);
            reject(new Error('Path is not a directory'));
            return;
          }
          
          resolve(finalPath);
        } catch (error) {
          console.log(`${TUIColors.FAIL}❌ Invalid path: ${finalPath}${TUIColors.ENDC}`);
          reject(error);
        }
        return;
      }
      
      // Handle TAB (ASCII 9)
      if (key[0] === 9) {
        const result = await getTabCompletion(currentInput);
        
        if (result.suggestions.length === 0) {
          // No matches - beep
          process.stdout.write('\x07');
        } else if (result.suggestions.length === 1) {
          // Single match - complete it
          const completion = result.completion;
          // Clear current line and rewrite with completion
          process.stdout.write('\r\x1b[K'); // Clear line
          process.stdout.write('📁 Enter project directory path: ' + completion);
          currentInput = completion;
          cursorPosition = completion.length;
        } else {
          // Multiple matches - show options
          console.log('\n');
          const suggestions = result.suggestions.map(s => path.basename(s)).join('  ');
          console.log(`${TUIColors.DIM}Options: ${suggestions}${TUIColors.ENDC}`);
          
          // Complete to common prefix if any
          if (result.completion !== currentInput) {
            currentInput = result.completion;
            cursorPosition = currentInput.length;
          }
          
          // Redraw prompt
          process.stdout.write('📁 Enter project directory path: ' + currentInput);
        }
        return;
      }
      
      // Handle Delete key (escape sequence \x1b[3~)
      if (keyStr === '\x1b[3~') {
        // Delete character at cursor (for now just ignore since we don't track cursor properly)
        return;
      }
      
      // Handle Arrow keys and other escape sequences
      if (keyStr.startsWith('\x1b[')) {
        // Ignore arrow keys and other escape sequences for now
        return;
      }
      
      // Handle Backspace (ASCII 8 or 127)
      if (key[0] === 8 || key[0] === 127) {
        if (currentInput.length > 0) {
          currentInput = currentInput.slice(0, -1);
          cursorPosition = currentInput.length;
          // Move cursor back and clear
          process.stdout.write('\b \b');
        }
        return;
      }
      
      // Handle printable characters
      if (keyStr.length === 1 && keyStr >= ' ' && keyStr <= '~') {
        currentInput += keyStr;
        cursorPosition = currentInput.length;
        process.stdout.write(keyStr);
        return;
      }
      
      // Ignore other non-printable characters
    });
  });
}

async function selectProjectDirectory(): Promise<string> {
  console.log(`${TUIColors.OKBLUE}${TUIColors.BOLD}📁 Project Directory Configuration${TUIColors.ENDC}`);
  console.log('This is the directory where agents will operate and execute tasks.');
  console.log();
  
  const currentDir = process.cwd();
  console.log(`Current directory: ${TUIColors.OKGREEN}${currentDir}${TUIColors.ENDC}`);
  console.log();
  
  const response = await inquirer.prompt({
    type: 'list',
    name: 'choice',
    message: 'Select project directory for agents:',
    choices: [
      { 
        name: `Use current directory (${currentDir})`, 
        value: 'current' 
      },
      { 
        name: 'Browse with tab completion (type and TAB)', 
        value: 'browse' 
      },
      { 
        name: 'Enter custom path manually', 
        value: 'manual' 
      }
    ]
  });
  
  if (response.choice === 'browse') {
    try {
      const selectedPath = await selectProjectDirectoryWithTabCompletion();
      console.log(`${TUIColors.OKGREEN}✅ Project directory set to: ${selectedPath}${TUIColors.ENDC}`);
      console.log();
      return selectedPath;
    } catch (error) {
      console.log(`${TUIColors.WARNING}⚠️  Selection cancelled, using current directory${TUIColors.ENDC}`);
      console.log();
      return currentDir;
    }
  }
  
  if (response.choice === 'manual') {
    const customPath = await inquirer.prompt({
      type: 'input',
      name: 'path',
      message: 'Enter absolute path to project directory:',
      default: currentDir,
      validate: async (input) => {
        if (!input || input.trim() === '') {
          return 'Path is required';
        }
        const trimmedPath = input.trim();
        const fs = await import('fs');
        const path = await import('path');
        const os = await import('os');
        
        let finalPath = trimmedPath;
        if (finalPath.startsWith('~')) {
          finalPath = finalPath.replace('~', os.homedir());
        }
        
        if (!path.isAbsolute(finalPath)) {
          return 'Please enter an absolute path (starting with / or C:\\)';
        }
        
        if (!fs.existsSync(finalPath)) {
          return `Directory does not exist: ${finalPath}`;
        }
        
        const stats = fs.statSync(finalPath);
        if (!stats.isDirectory()) {
          return `Path is not a directory: ${finalPath}`;
        }
        
        return true;
      }
    });
    
    let finalPath = customPath.path.trim();
    if (finalPath.startsWith('~')) {
      const os = await import('os');
      finalPath = finalPath.replace('~', os.homedir());
    }
    
    console.log(`${TUIColors.OKGREEN}✅ Project directory set to: ${finalPath}${TUIColors.ENDC}`);
    console.log();
    return finalPath;
  }
  
  console.log(`${TUIColors.OKGREEN}✅ Using current directory as project directory${TUIColors.ENDC}`);
  console.log();
  return currentDir;
}

async function selectServerPort(): Promise<number> {
  console.log(`${TUIColors.OKBLUE}${TUIColors.BOLD}🌐 Server Port Configuration${TUIColors.ENDC}`);
  console.log();
  
  const availablePorts = await getPortRecommendations();
  
  if (availablePorts.length === 0) {
    console.log(`${TUIColors.WARNING}⚠️  No common ports available, finding alternative...${TUIColors.ENDC}`);
    const alternativePort = await findAvailablePort(3001, 9999);
    return alternativePort;
  }
  
  console.log('Available Ports Found:');
  availablePorts.forEach(port => {
    console.log(`  Port ${port}: ${TUIColors.OKGREEN}✅ Available${TUIColors.ENDC}`);
  });
  console.log();
  
  const choices = [
    ...availablePorts.map(port => ({
      name: `Port ${port} - Available`,
      value: port,
      short: `${port}`
    })),
    { name: 'Enter custom port', value: 'custom', short: 'Custom' }
  ];
  
  const portChoice = await inquirer.prompt({
    type: 'list',
    name: 'port',
    message: 'Select server port:',
    choices
  });
  
  if (portChoice.port === 'custom') {
    const customPort = await inquirer.prompt({
      type: 'number',
      name: 'port',
      message: 'Enter port number (1024-65535):',
      validate: async (input) => {
        if (!input || input < 1024 || input > 65535) {
          return 'Port must be between 1024 and 65535';
        }
        if (!(await isPortAvailable(input))) {
          return `Port ${input} is already in use`;
        }
        return true;
      }
    });
    return customPort.port;
  }
  
  return portChoice.port;
}

async function configureApiKeys(embeddingProvider: string): Promise<void> {
  console.log(`${TUIColors.OKBLUE}${TUIColors.BOLD}🔑 API Key Configuration${TUIColors.ENDC}`);
  console.log();
  
  const currentEnvVars = getCurrentEnvValues();
  const embeddingVars = getEnvVariablesByCategory('embedding');
  const cliVars = getEnvVariablesByCategory('cli');
  
  const neededKeys = embeddingVars.filter(envVar => {
    switch (embeddingProvider) {
      case 'openai': return envVar.key === 'OPENAI_API_KEY';
      case 'huggingface': return envVar.key === 'HUGGINGFACE_API_KEY';
      case 'gemini': return envVar.key === 'GEMINI_API_KEY';
      default: return false;
    }
  });
  
  neededKeys.push(...cliVars);
  
  if (neededKeys.length === 0) {
    console.log(`${TUIColors.OKGREEN}✅ No API keys required for ${embeddingProvider} provider${TUIColors.ENDC}`);
    console.log();
    return;
  }
  
  console.log('Current API Key Status:');
  for (const envVar of neededKeys) {
    const currentValue = currentEnvVars.get(envVar.key);
    const status = currentValue ? 
      `${TUIColors.OKGREEN}✅ Set (${maskApiKey(currentValue)})${TUIColors.ENDC}` :
      `${TUIColors.WARNING}❌ Not set${TUIColors.ENDC}`;
    console.log(`  ${envVar.key}: ${status}`);
  }
  console.log();
  
  const configureKeys = await inquirer.prompt({
    type: 'confirm',
    name: 'configure',
    message: 'Do you want to configure API keys now?',
    default: true
  });
  
  if (!configureKeys.configure) {
    return;
  }
  
  for (const envVar of neededKeys) {
    const currentValue = currentEnvVars.get(envVar.key);
    
    console.log(`\n${TUIColors.OKBLUE}Configuring ${envVar.key}${TUIColors.ENDC}`);
    console.log(`Description: ${envVar.description}`);
    
    if (currentValue) {
      console.log(`Current value: ${maskApiKey(currentValue)}`);
    }
    
    const keyConfig = await inquirer.prompt([
      {
        type: 'list',
        name: 'action',
        message: `What would you like to do with ${envVar.key}?`,
        choices: [
          { name: currentValue ? 'Keep current value' : 'Skip for now', value: 'keep' },
          { name: 'Set new value', value: 'set' },
          { name: 'Clear value', value: 'clear', disabled: !currentValue }
        ]
      }
    ]);
    
    if (keyConfig.action === 'set') {
      const keyValue = await inquirer.prompt({
        type: 'password',
        name: 'value',
        message: `Enter ${envVar.key}:`,
        mask: '*',
        validate: (input) => {
          const validation = validateApiKey(envVar.key, input);
          if (!validation.valid) {
            return validation.message || 'Invalid API key format';
          }
          return true;
        }
      });
      
      setEnvVariable(envVar.key, keyValue.value);
      console.log(`${TUIColors.OKGREEN}✅ ${envVar.key} saved successfully${TUIColors.ENDC}`);
      
    } else if (keyConfig.action === 'clear' && currentValue) {
      setEnvVariable(envVar.key, '');
      console.log(`${TUIColors.WARNING}🗑️ ${envVar.key} cleared${TUIColors.ENDC}`);
    }
  }
  
  reloadEnvironmentVariables();
  
  console.log(`\n${TUIColors.OKGREEN}✅ API key configuration complete${TUIColors.ENDC}`);
  console.log();
}

async function selectEmbeddingProvider(): Promise<string> {
  console.log(`${TUIColors.OKBLUE}${TUIColors.BOLD}📊 Embedding Provider Configuration${TUIColors.ENDC}`);
  console.log();
  
  const providerChoices = Object.entries(EMBEDDING_PROVIDERS).map(([key, provider]) => ({
    name: `${provider.recommended ? '⭐ ' : '   '}${provider.name} - ${provider.description}`,
    value: key,
    short: provider.name
  }));

  const response = await inquirer.prompt({
    type: 'list',
    name: 'provider',
    message: 'Select your embedding provider:',
    choices: providerChoices,
    pageSize: 10
  });

  await configureApiKeys(response.provider);
  
  return response.provider;
}

async function selectCLIAgents(): Promise<string[]> {
  console.log(`${TUIColors.OKBLUE}${TUIColors.BOLD}🤖 CLI Agent Selection${TUIColors.ENDC}`);
  console.log('Choose which CLI agents you want available for background tasks:');
  console.log();

  const cliChoices = Object.entries(CLI_AGENTS).map(([key, agent]) => ({
    name: `${agent.recommended ? '⭐ ' : '   '}${agent.name} - ${agent.description}${agent.mcpSupport ? ' [MCP]' : ''}`,
    value: key,
    checked: agent.recommended
  }));

  const response = await inquirer.prompt({
    type: 'checkbox',
    name: 'agents',
    message: 'Select CLI agents (space to toggle, enter to confirm):',
    choices: cliChoices,
    validate: (input) => {
      if (input.length === 0) {
        return 'Please select at least one CLI agent';
      }
      return true;
    }
  });

  console.log();
  return response.agents;
}

async function selectConfigurationMode(): Promise<ToolCategories | 'custom'> {
  console.log(`${TUIColors.OKBLUE}${TUIColors.BOLD}⚙️  Tool Configuration${TUIColors.ENDC}`);
  console.log();

  const modeChoices = Object.entries(PREDEFINED_MODES).map(([key, mode]) => ({
    name: `${mode.name} - ${mode.description}`,
    value: key,
    short: mode.name
  }));

  modeChoices.push({
    name: 'Custom Configuration - Choose individual tool categories',
    value: 'custom',
    short: 'Custom'
  });

  const response = await inquirer.prompt({
    type: 'list',
    name: 'mode',
    message: 'Select configuration mode:',
    choices: modeChoices,
    pageSize: 10
  });

  if (response.mode === 'custom') {
    return 'custom';
  }

  const selectedMode = PREDEFINED_MODES[response.mode];
  if (!selectedMode) {
    throw new Error(`Unknown mode: ${response.mode}`);
  }
  return selectedMode.categories;
}

async function selectCustomTools(): Promise<ToolCategories> {
  console.log(`${TUIColors.OKBLUE}${TUIColors.BOLD}🔧 Custom Tool Selection${TUIColors.ENDC}`);
  console.log();

  const currentConfig = loadToolConfig();
  
  const toolChoices = [
    { key: 'basic' as keyof ToolCategories, name: 'Basic Tools', description: 'Health checks, system status (always enabled)', disabled: true },
    { key: 'rag' as keyof ToolCategories, name: 'RAG/Vector Search', description: 'Document search and knowledge retrieval' },
    { key: 'memory' as keyof ToolCategories, name: 'Memory & Context', description: 'Project context and session memory' },
    { key: 'agentManagement' as keyof ToolCategories, name: 'Agent Management', description: 'Create, manage, and coordinate agents' },
    { key: 'taskManagement' as keyof ToolCategories, name: 'Task Management', description: 'Task creation and hierarchical workflows' },
    { key: 'fileManagement' as keyof ToolCategories, name: 'File Management', description: 'File operations and project management' },
    { key: 'agentCommunication' as keyof ToolCategories, name: 'Agent Communication', description: 'Inter-agent messaging and coordination' },
    { key: 'sessionState' as keyof ToolCategories, name: 'Session State', description: 'Session persistence and recovery' },
    { key: 'assistanceRequest' as keyof ToolCategories, name: 'Assistance Requests', description: 'Intelligent help and support' },
    { key: 'backgroundAgents' as keyof ToolCategories, name: 'Background Agents', description: 'Standalone agents without task hierarchy' }
  ];

  const checkboxChoices = toolChoices.map(tool => ({
    name: tool.disabled ? 
      `${tool.name} - ${tool.description} [REQUIRED]` :
      `${tool.name} - ${tool.description}`,
    value: tool.key,
    checked: currentConfig[tool.key],
    disabled: tool.disabled
  }));

  const response = await inquirer.prompt({
    type: 'checkbox',
    name: 'tools',
    message: 'Select tool categories (space to toggle, enter to confirm):',
    choices: checkboxChoices,
    pageSize: 15
  });

  const config: ToolCategories = {
    basic: true,
    rag: false,
    memory: false,
    agentManagement: false,
    taskManagement: false,
    fileManagement: false,
    agentCommunication: false,
    sessionState: false,
    assistanceRequest: false,
    backgroundAgents: false
  };

  response.tools.forEach((tool: string) => {
    config[tool as keyof ToolCategories] = true;
  });

  console.log();
  return config;
}

function displayConfigurationSummary(
  config: ToolCategories,
  embeddingProvider: string,
  cliAgents: string[],
  serverPort: number,
  projectDirectory: string
) {
  console.log(`${TUIColors.HEADER}${TUIColors.BOLD}📋 Configuration Summary${TUIColors.ENDC}`);
  console.log('━'.repeat(50));
  console.log();
  
  console.log(`${TUIColors.OKBLUE}📁 Project Directory:${TUIColors.ENDC} ${projectDirectory}`);
  console.log(`${TUIColors.OKBLUE}🌐 Server Port:${TUIColors.ENDC} ${serverPort}`);
  console.log();
  
  const provider = EMBEDDING_PROVIDERS[embeddingProvider as keyof typeof EMBEDDING_PROVIDERS];
  console.log(`${TUIColors.OKBLUE}📊 Embedding Provider:${TUIColors.ENDC} ${provider.name}`);
  console.log();
  
  console.log(`${TUIColors.OKBLUE}🤖 Available CLI Agents:${TUIColors.ENDC}`);
  cliAgents.forEach(agentKey => {
    const agent = CLI_AGENTS[agentKey as keyof typeof CLI_AGENTS];
    console.log(`   • ${agent.name}${agent.mcpSupport ? ' [MCP]' : ''}`);
  });
  console.log();
  
  console.log(`${TUIColors.OKBLUE}🔧 Enabled Tool Categories:${TUIColors.ENDC}`);
  Object.entries(config)
    .filter(([_, enabled]) => enabled)
    .forEach(([category, _]) => {
      console.log(`   • ${getCategoryDescription(category as keyof ToolCategories)}`);
    });
  
  console.log();
  console.log('━'.repeat(50));
}

export async function launchPracticalConfigurationTUI(): Promise<{
  toolConfig: ToolCategories;
  embeddingProvider: string;
  cliAgents: string[];
  serverPort: number;
  projectDirectory: string;
  configName?: string;
}> {
  displayHeader();
  
  const existingConfig = await handleNamedConfigurations();
  
  if (existingConfig) {
    console.log(`${TUIColors.OKGREEN}✅ Loaded saved configuration: ${existingConfig.configName}${TUIColors.ENDC}`);
    console.log(`${TUIColors.DIM}You can now update the port and project directory settings...${TUIColors.ENDC}`);
    console.log();
    
    // Always ask for port and project directory even when loading existing config
    const projectDirectory = await selectProjectDirectory();
    const serverPort = await selectServerPort();
    
    return {
      toolConfig: existingConfig.toolCategories,
      embeddingProvider: existingConfig.embeddingProvider,
      cliAgents: existingConfig.cliAgents,
      serverPort: serverPort,
      projectDirectory: projectDirectory,
      configName: existingConfig.configName
    };
  }
  
  const projectDirectory = await selectProjectDirectory();
  const serverPort = await selectServerPort();
  const embeddingProvider = await selectEmbeddingProvider();
  const cliAgents = await selectCLIAgents();
  
  const configMode = await selectConfigurationMode();
  let toolConfig: ToolCategories;
  
  if (configMode === 'custom') {
    toolConfig = await selectCustomTools();
  } else {
    toolConfig = configMode as ToolCategories;
  }
  
  displayConfigurationSummary(toolConfig, embeddingProvider, cliAgents, serverPort, projectDirectory);
  
  const confirm = await inquirer.prompt({
    type: 'confirm',
    name: 'proceed',
    message: 'Proceed with this configuration?',
    default: true
  });
  
  if (!confirm.proceed) {
    console.log(`${TUIColors.WARNING}⚠️  Configuration cancelled${TUIColors.ENDC}`);
    process.exit(0);
  }
  
  const saveConfig = await inquirer.prompt({
    type: 'confirm',
    name: 'save',
    message: 'Would you like to save this configuration for future use?',
    default: true
  });
  
  let configName: string | undefined;
  
  if (saveConfig.save) {
    const configDetails = await inquirer.prompt([
      {
        type: 'input',
        name: 'name',
        message: 'Enter a name for this configuration:',
        validate: (input) => {
          if (!input || input.trim() === '') {
            return 'Configuration name is required';
          }
          if (input.length > 50) {
            return 'Configuration name must be 50 characters or less';
          }
          return true;
        }
      },
      {
        type: 'input',
        name: 'description',
        message: 'Enter a description (optional):',
        default: `Custom configuration created ${new Date().toLocaleDateString()}`
      }
    ]);
    
    configName = configDetails.name.trim();
    
    const namedConfigData: ExtendedConfig = {
      toolCategories: toolConfig,
      embeddingProvider,
      cliAgents,
      serverPort,
      projectDirectory,
      configName,
      advancedSettings: {
        embeddingModel: 'text-embedding-3-large',
        embeddingDimensions: 1536,
        maxBatchSize: 100,
        cliAgentTimeout: 30000,
        defaultCLI: cliAgents.includes('claude') ? 'claude' : (cliAgents[0] || 'claude')
      },
      lastUpdated: new Date().toISOString()
    };
    
    saveNamedConfig(configName || 'unnamed', configDetails.description || '', namedConfigData);
    console.log(`${TUIColors.OKGREEN}✅ Configuration '${configName}' saved successfully${TUIColors.ENDC}`);
  }
  
  const toolValidation = validateToolConfig(toolConfig);
  if (!toolValidation.valid) {
    console.log(`${TUIColors.FAIL}❌ Tool configuration warnings:${TUIColors.ENDC}`);
    toolValidation.warnings.forEach((warning: string) => console.log(`   • ${warning}`));
    console.log();
  }
  
  const providerValidation = validateEmbeddingProviderConfig(embeddingProvider);
  if (!providerValidation.valid) {
    console.log(`${TUIColors.WARNING}⚠️  Embedding provider warnings:${TUIColors.ENDC}`);
    providerValidation.errors.forEach(error => console.log(`   • ${error}`));
    console.log();
  }
  
  const extendedConfig: ExtendedConfig = {
    toolCategories: toolConfig,
    embeddingProvider,
    cliAgents,
    serverPort,
    projectDirectory,
    configName,
    advancedSettings: {
      embeddingModel: 'text-embedding-3-large',
      embeddingDimensions: 1536,
      maxBatchSize: 100,
      cliAgentTimeout: 30000,
      defaultCLI: cliAgents.includes('claude') ? 'claude' : (cliAgents[0] || 'claude')
    },
    lastUpdated: new Date().toISOString()
  };
  
  saveExtendedConfig(extendedConfig);
  saveToolConfig(toolConfig);
  setEnvVariable('EMBEDDING_PROVIDER', embeddingProvider);
  
  console.log(`${TUIColors.OKGREEN}✅ Configuration saved successfully${TUIColors.ENDC}`);
  console.log();
  
  return {
    toolConfig,
    embeddingProvider,
    cliAgents,
    serverPort,
    projectDirectory,
    configName
  };
}