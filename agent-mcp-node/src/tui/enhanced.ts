// Enhanced TUI for Agent-MCP with improved visuals and UX
// Modern, animated, and user-friendly configuration interface

import inquirer from 'inquirer';
import { 
  ToolCategories, 
  PREDEFINED_MODES, 
  DEFAULT_CONFIG,
  loadToolConfig, 
  saveToolConfig, 
  getConfigMode,
  validateToolConfig,
  getCategoryDescription,
  getEnabledCategories,
  getDisabledCategories
} from '../core/toolConfig.js';
import { TUIColors, VERSION } from '../core/config.js';

// Enhanced color palette for better visual hierarchy
const Colors = {
  ...TUIColors,
  ACCENT: '\x1b[38;5;208m',    // Orange accent
  SUCCESS: '\x1b[38;5;46m',    // Bright green
  INFO: '\x1b[38;5;117m',      // Sky blue
  SECONDARY: '\x1b[38;5;245m', // Gray
  PURPLE: '\x1b[38;5;141m',    // Light purple
  PINK: '\x1b[38;5;205m',      // Pink
} as const;

// Box drawing characters for better UI
const Box = {
  TOP_LEFT: '╔',
  TOP_RIGHT: '╗',
  BOTTOM_LEFT: '╚',
  BOTTOM_RIGHT: '╝',
  HORIZONTAL: '═',
  VERTICAL: '║',
  T_DOWN: '╦',
  T_UP: '╩',
  T_RIGHT: '╠',
  T_LEFT: '╣',
  CROSS: '╬',
  LIGHT_HORIZONTAL: '─',
  LIGHT_VERTICAL: '│',
  LIGHT_TOP_LEFT: '┌',
  LIGHT_TOP_RIGHT: '┐',
  LIGHT_BOTTOM_LEFT: '└',
  LIGHT_BOTTOM_RIGHT: '┘',
} as const;

// Utility functions for enhanced UI
function createBox(title: string, content: string[], width: number = 70): string {
  const lines: string[] = [];
  const titlePadding = Math.max(0, (width - title.length - 4) / 2);
  const titleLine = '║' + ' '.repeat(Math.floor(titlePadding)) + 
                   `${Colors.BOLD}${title}${Colors.ENDC}` + 
                   ' '.repeat(Math.ceil(titlePadding)) + '║';
  
  lines.push(`${Colors.INFO}${Box.TOP_LEFT}${Box.HORIZONTAL.repeat(width - 2)}${Box.TOP_RIGHT}${Colors.ENDC}`);
  lines.push(`${Colors.INFO}${titleLine}${Colors.ENDC}`);
  lines.push(`${Colors.INFO}${Box.T_RIGHT}${Box.HORIZONTAL.repeat(width - 2)}${Box.T_LEFT}${Colors.ENDC}`);
  
  content.forEach(line => {
    const padding = Math.max(0, width - line.replace(/\x1b\[[0-9;]*m/g, '').length - 4);
    lines.push(`${Colors.INFO}║${Colors.ENDC} ${line}${' '.repeat(padding)} ${Colors.INFO}║${Colors.ENDC}`);
  });
  
  lines.push(`${Colors.INFO}${Box.BOTTOM_LEFT}${Box.HORIZONTAL.repeat(width - 2)}${Box.BOTTOM_RIGHT}${Colors.ENDC}`);
  return lines.join('\n');
}

function createProgressBar(current: number, total: number, width: number = 30): string {
  const filled = Math.round((current / total) * width);
  const empty = width - filled;
  const percentage = Math.round((current / total) * 100);
  
  return `${Colors.ACCENT}[${'█'.repeat(filled)}${Colors.SECONDARY}${'░'.repeat(empty)}${Colors.ACCENT}] ${percentage}%${Colors.ENDC}`;
}

function animatedLoading(text: string, duration: number = 1500): Promise<void> {
  return new Promise((resolve) => {
    const frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];
    let i = 0;
    
    const interval = setInterval(() => {
      process.stdout.write(`\r${Colors.INFO}${frames[i]}${Colors.ENDC} ${text}`);
      i = (i + 1) % frames.length;
    }, 100);
    
    setTimeout(() => {
      clearInterval(interval);
      process.stdout.write(`\r${Colors.SUCCESS}✓${Colors.ENDC} ${text}\n`);
      resolve();
    }, duration);
  });
}

function typeEffect(text: string, delay: number = 30): Promise<void> {
  return new Promise((resolve) => {
    let i = 0;
    const interval = setInterval(() => {
      if (i < text.length) {
        process.stdout.write(text[i] || '');
        i++;
      } else {
        clearInterval(interval);
        process.stdout.write('\n');
        resolve();
      }
    }, delay);
  });
}

export async function launchEnhancedPreConfigurationTUI(): Promise<ToolCategories> {
  console.clear();
  
  // Animated welcome banner
  await displayEnhancedWelcomeBanner();
  
  const currentConfig = loadToolConfig();
  const currentMode = getConfigMode(currentConfig);
  
  // Show current configuration in a beautiful box
  if (currentMode || getEnabledCategories(currentConfig).length < Object.keys(DEFAULT_CONFIG).length) {
    await displayCurrentConfiguration(currentConfig, currentMode);
  }

  // Enhanced main menu
  const mainChoice = await showMainMenu();
  let finalConfig: ToolCategories;

  // Loading animation for each choice
  await animatedLoading(`Preparing ${mainChoice.short} configuration...`);

  switch (mainChoice.action) {
    case 'quickstart':
      finalConfig = await handleEnhancedQuickStart();
      break;
    case 'predefined':
      finalConfig = await handleEnhancedPredefinedModeSelection();
      break;
    case 'custom':
      finalConfig = await handleEnhancedCustomConfiguration();
      break;
    case 'advanced':
      finalConfig = await handleEnhancedAdvancedSetup();
      break;
    case 'current':
    default:
      finalConfig = currentConfig.basic !== undefined ? currentConfig : DEFAULT_CONFIG;
      break;
  }

  // Validation and confirmation
  const validation = validateToolConfig(finalConfig);
  if (validation.warnings.length > 0) {
    await showValidationWarnings(validation.warnings);
  }

  // Save configuration with animation
  await animatedLoading('Saving configuration...');
  saveToolConfig(finalConfig, getConfigMode(finalConfig) || 'custom');

  // Final summary
  await displayConfigurationSummary(finalConfig);
  
  await animatedLoading('Starting Agent-MCP server...', 2000);
  console.log('');
  
  return finalConfig;
}

async function displayEnhancedWelcomeBanner(): Promise<void> {
  const banner = [
    '',
    `${Colors.PURPLE}    ╔═══════════════════════════════════════════════════════════════════════════╗${Colors.ENDC}`,
    `${Colors.PURPLE}    ║                                                                           ║${Colors.ENDC}`,
    `${Colors.PURPLE}    ║         ${Colors.BOLD}${Colors.ACCENT}🤖 Agent-MCP Configuration Wizard${Colors.ENDC}${Colors.PURPLE}  v${VERSION}             ║${Colors.ENDC}`,
    `${Colors.PURPLE}    ║                                                                           ║${Colors.ENDC}`,
    `${Colors.PURPLE}    ║     ${Colors.INFO}Configure your Multi-Agent Collaboration Platform${Colors.ENDC}${Colors.PURPLE}           ║${Colors.ENDC}`,
    `${Colors.PURPLE}    ║     ${Colors.SECONDARY}Customize tools, modes, and capabilities before launch${Colors.ENDC}${Colors.PURPLE}         ║${Colors.ENDC}`,
    `${Colors.PURPLE}    ║                                                                           ║${Colors.ENDC}`,
    `${Colors.PURPLE}    ╚═══════════════════════════════════════════════════════════════════════════╝${Colors.ENDC}`,
    '',
  ];
  
  // Type out the banner with animation
  for (const line of banner) {
    if (line.trim()) {
      await typeEffect(line, 10);
    } else {
      console.log();
    }
  }
}

async function displayCurrentConfiguration(config: ToolCategories, mode: string | null): Promise<void> {
  const enabledCategories = getEnabledCategories(config);
  const disabledCategories = getDisabledCategories(config);
  const totalCategories = Object.keys(config).length;
  
  const content = [
    mode && PREDEFINED_MODES[mode] 
      ? `${Colors.SUCCESS}Mode:${Colors.ENDC} ${PREDEFINED_MODES[mode].name}`
      : `${Colors.WARNING}Mode:${Colors.ENDC} Custom Configuration`,
    '',
    `${Colors.INFO}Status:${Colors.ENDC} ${createProgressBar(enabledCategories.length, totalCategories)}`,
    `${Colors.SUCCESS}Enabled:${Colors.ENDC} ${enabledCategories.join(', ')}`,
  ];
  
  if (disabledCategories.length > 0) {
    content.push(`${Colors.SECONDARY}Disabled:${Colors.ENDC} ${disabledCategories.join(', ')}`);
  }
  
  if (mode && PREDEFINED_MODES[mode]) {
    content.push('', `${Colors.ACCENT}Description:${Colors.ENDC} ${PREDEFINED_MODES[mode].description}`);
  }
  
  console.log(createBox('Current Configuration', content));
  console.log('');
}

async function showMainMenu(): Promise<any> {
  const menuItems = [
    {
      name: `${Colors.SUCCESS}🚀 Quick Start${Colors.ENDC} - Get started in seconds with recommended settings`,
      value: 'quickstart',
      short: 'Quick Start'
    },
    {
      name: `${Colors.INFO}🎯 Choose Mode${Colors.ENDC} - Select from optimized pre-built configurations`,
      value: 'predefined',
      short: 'Predefined Mode'
    },
    {
      name: `${Colors.ACCENT}🔧 Custom Build${Colors.ENDC} - Handpick exactly which tools you want`,
      value: 'custom',
      short: 'Custom Config'
    },
    {
      name: `${Colors.PURPLE}📊 Advanced Setup${Colors.ENDC} - Detailed configuration with explanations`,
      value: 'advanced',
      short: 'Advanced Setup'
    },
    new inquirer.Separator(`${Colors.SECONDARY}──────────────────────────────────────────────────────────${Colors.ENDC}`),
    {
      name: `${Colors.SECONDARY}✅ Continue${Colors.ENDC} - Use current/default configuration`,
      value: 'current',
      short: 'Use Current'
    }
  ];

  return inquirer.prompt({
    type: 'list',
    name: 'action',
    message: `${Colors.BOLD}How would you like to configure Agent-MCP?${Colors.ENDC}`,
    choices: menuItems,
    pageSize: 12
  });
}

async function handleEnhancedQuickStart(): Promise<ToolCategories> {
  console.clear();
  
  const content = [
    `${Colors.INFO}Perfect for getting started quickly!${Colors.ENDC}`,
    '',
    `${Colors.SUCCESS}🎯 Memory + RAG Mode (Recommended)${Colors.ENDC}`,
    '  • Perfect for code assistance and knowledge work',
    '  • Includes vector search and context memory',
    '  • Lightweight and fast (~15 tools)',
    '  • No complex orchestration overhead',
    '',
    `${Colors.ACCENT}🔥 Full Mode${Colors.ENDC}`,
    '  • Complete agent orchestration platform',
    '  • Multi-agent coordination and task management', 
    '  • All features enabled (~35+ tools)',
    '  • Resource intensive but feature-complete',
    '',
    `${Colors.SECONDARY}⚡ Minimal Mode${Colors.ENDC}`,
    '  • Basic health checks only',
    '  • Fastest startup time',
    '  • Good for testing connectivity',
  ];
  
  console.log(createBox('🚀 Quick Start Options', content));
  console.log('');

  const choice = await inquirer.prompt({
    type: 'list',
    name: 'mode',
    message: `${Colors.BOLD}Select your quick start option:${Colors.ENDC}`,
    choices: [
      {
        name: `${Colors.SUCCESS}🎯 Memory + RAG Mode${Colors.ENDC} (Recommended for most users)`,
        value: 'memoryRag',
        short: 'Memory + RAG'
      },
      {
        name: `${Colors.ACCENT}🔥 Full Mode${Colors.ENDC} (All features enabled)`,
        value: 'full', 
        short: 'Full Mode'
      },
      {
        name: `${Colors.SECONDARY}⚡ Minimal Mode${Colors.ENDC} (Fastest, basic only)`,
        value: 'minimal',
        short: 'Minimal'
      },
      {
        name: `${Colors.INFO}🎯 Background Agents${Colors.ENDC} (Standalone agents mode)`,
        value: 'background',
        short: 'Background'
      }
    ]
  });

  const selectedMode = PREDEFINED_MODES[choice.mode];
  if (!selectedMode) {
    throw new Error(`Invalid mode selection: ${choice.mode}`);
  }

  await animatedLoading(`Configuring ${selectedMode.name}...`);
  console.log(`${Colors.SUCCESS}✅ Quick start configured: ${selectedMode.name}${Colors.ENDC}\n`);
  
  return selectedMode.categories;
}

async function handleEnhancedPredefinedModeSelection(): Promise<ToolCategories> {
  console.clear();
  
  const modeChoices = Object.entries(PREDEFINED_MODES).map(([key, mode]) => {
    const toolCount = Object.values(mode.categories).filter(Boolean).length;
    const totalCategories = Object.keys(mode.categories).length;
    const percentage = Math.round((toolCount / totalCategories) * 100);
    
    // Color code based on complexity
    let colorCode: string = Colors.INFO;
    if (toolCount <= 3) colorCode = Colors.SUCCESS;
    else if (toolCount >= 8) colorCode = Colors.ACCENT;
    
    return {
      name: `${colorCode}${mode.name}${Colors.ENDC} - ${mode.description}\n   ${createProgressBar(toolCount, totalCategories, 20)} ${toolCount}/${totalCategories} categories`,
      value: key,
      short: mode.name
    };
  });

  console.log(createBox('🎯 Predefined Configuration Modes', [
    'Choose from carefully optimized configurations:',
    '',
    `${Colors.SUCCESS}Green${Colors.ENDC} = Lightweight • ${Colors.INFO}Blue${Colors.ENDC} = Balanced • ${Colors.ACCENT}Orange${Colors.ENDC} = Feature-rich`
  ]));
  console.log('');

  const modeChoice = await inquirer.prompt({
    type: 'list',
    name: 'mode',
    message: `${Colors.BOLD}Select a configuration mode:${Colors.ENDC}`,
    choices: modeChoices,
    pageSize: 8
  });

  const selectedMode = PREDEFINED_MODES[modeChoice.mode];
  if (!selectedMode) {
    throw new Error(`Invalid mode selection: ${modeChoice.mode}`);
  }

  await animatedLoading(`Loading ${selectedMode.name}...`);
  console.log(`${Colors.SUCCESS}✅ Selected: ${selectedMode.name}${Colors.ENDC}\n`);
  
  return selectedMode.categories;
}

async function handleEnhancedCustomConfiguration(): Promise<ToolCategories> {
  console.clear();
  
  console.log(createBox('🔧 Custom Tool Configuration', [
    'Build your perfect configuration by selecting exactly the tools you need.',
    '',
    `${Colors.SECONDARY}Basic tools are always included for system health.${Colors.ENDC}`,
    `${Colors.INFO}Use SPACE to select/deselect, ENTER to confirm${Colors.ENDC}`
  ]));
  console.log('');

  const categories = Object.entries(DEFAULT_CONFIG)
    .filter(([key]) => key !== 'basic') // Basic is always enabled
    .map(([key, _]) => {
      const description = getCategoryDescription(key as keyof ToolCategories);
      const icon = getCategoryIcon(key as keyof ToolCategories);
      return {
        name: `${icon} ${Colors.BOLD}${key}${Colors.ENDC}\n   ${Colors.SECONDARY}${description}${Colors.ENDC}`,
        value: key,
        checked: false // Start with none selected for custom build
      };
    });

  const selectedCategories = await inquirer.prompt({
    type: 'checkbox',
    name: 'categories',
    message: `${Colors.BOLD}Select the tool categories you want to enable:${Colors.ENDC}`,
    choices: categories,
    pageSize: 12,
    validate: (selections: any) => {
      if (selections.length === 0) {
        return 'Please select at least one category (basic tools are always enabled)';
      }
      return true;
    }
  });

  // Build configuration
  const newConfig: ToolCategories = {
    basic: true, // Always enabled
    rag: selectedCategories.categories.includes('rag'),
    memory: selectedCategories.categories.includes('memory'),
    agentManagement: selectedCategories.categories.includes('agentManagement'),
    taskManagement: selectedCategories.categories.includes('taskManagement'),
    fileManagement: selectedCategories.categories.includes('fileManagement'),
    agentCommunication: selectedCategories.categories.includes('agentCommunication'),
    sessionState: selectedCategories.categories.includes('sessionState'),
    assistanceRequest: selectedCategories.categories.includes('assistanceRequest'),
    backgroundAgents: selectedCategories.categories.includes('backgroundAgents')
  };

  await animatedLoading('Building custom configuration...');
  console.log(`${Colors.SUCCESS}✅ Custom configuration created${Colors.ENDC}\n`);
  
  return newConfig;
}

async function handleEnhancedAdvancedSetup(): Promise<ToolCategories> {
  console.clear();
  
  console.log(createBox('📊 Advanced Configuration Setup', [
    'We\'ll walk through each tool category with detailed explanations.',
    'This gives you complete control over your Agent-MCP setup.',
    '',
    `${Colors.INFO}You can enable dependencies automatically when needed.${Colors.ENDC}`
  ]));
  console.log('');
  
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
  
  const categories: Array<{key: keyof ToolCategories, name: string, deps?: string[]}> = [
    { key: 'rag', name: 'RAG (Retrieval Augmented Generation)' },
    { key: 'memory', name: 'Memory & Project Context' },
    { key: 'fileManagement', name: 'File Management' },
    { key: 'sessionState', name: 'Session State & Persistence' },
    { key: 'assistanceRequest', name: 'Intelligent Assistance' },
    { key: 'agentManagement', name: 'Agent Management & Orchestration' },
    { key: 'taskManagement', name: 'Task Management & Workflows', deps: ['agentManagement'] },
    { key: 'agentCommunication', name: 'Inter-Agent Communication', deps: ['agentManagement'] },
    { key: 'backgroundAgents', name: 'Background Agents (Standalone)' }
  ];

  for (let i = 0; i < categories.length; i++) {
    const category = categories[i];
    if (!category) continue;
    
    const progress = createProgressBar(i + 1, categories.length, 25);
    
    console.clear();
    console.log(`${Colors.HEADER}📊 Advanced Setup${Colors.ENDC} ${progress}\n`);
    
    const content = [
      `${Colors.BOLD}${getCategoryIcon(category.key)} ${category.name}${Colors.ENDC}`,
      '',
      getCategoryDescription(category.key),
      ''
    ];
    
    if (category.deps) {
      content.push(`${Colors.WARNING}Dependencies:${Colors.ENDC} Requires ${category.deps.join(', ')}`);
      content.push('');
    }
    
    console.log(createBox(`Category ${i + 1}/${categories.length}`, content));
    
    const enableChoice = await inquirer.prompt({
      type: 'confirm',
      name: 'enable',
      message: `Enable ${category.name}?`,
      default: false
    });
    
    config[category.key] = enableChoice.enable;
    
    // Auto-enable dependencies
    if (enableChoice.enable && category.deps) {
      for (const dep of category.deps) {
        if (!config[dep as keyof ToolCategories]) {
          const depChoice = await inquirer.prompt({
            type: 'confirm',
            name: 'enableDep',
            message: `${Colors.WARNING}${category.name} requires ${dep}. Enable it?${Colors.ENDC}`,
            default: true
          });
          
          if (depChoice.enableDep) {
            config[dep as keyof ToolCategories] = true;
            console.log(`${Colors.SUCCESS}✓ ${dep} enabled automatically${Colors.ENDC}`);
          }
        }
      }
    }
  }
  
  await animatedLoading('Finalizing advanced configuration...');
  console.log(`${Colors.SUCCESS}✅ Advanced configuration completed${Colors.ENDC}\n`);
  
  return config;
}

async function showValidationWarnings(warnings: string[]): Promise<void> {
  if (warnings.length === 0) return;
  
  const content = warnings.map(warning => `${Colors.WARNING}⚠${Colors.ENDC} ${warning}`);
  console.log(createBox('Configuration Warnings', content));
  
  const continueChoice = await inquirer.prompt({
    type: 'confirm',
    name: 'continue',
    message: 'Continue with these warnings?',
    default: true
  });
  
  if (!continueChoice.continue) {
    process.exit(0);
  }
  console.log('');
}

async function displayConfigurationSummary(config: ToolCategories): Promise<void> {
  const enabledCategories = getEnabledCategories(config);
  const mode = getConfigMode(config);
  const totalCategories = Object.keys(config).length;
  
  const content = [
    mode && PREDEFINED_MODES[mode] 
      ? `${Colors.SUCCESS}Mode:${Colors.ENDC} ${PREDEFINED_MODES[mode].name}`
      : `${Colors.ACCENT}Mode:${Colors.ENDC} Custom Configuration`,
    '',
    `${Colors.INFO}Categories enabled:${Colors.ENDC} ${createProgressBar(enabledCategories.length, totalCategories)}`,
    '',
    ...enabledCategories.map(cat => 
      `${Colors.SUCCESS}✓${Colors.ENDC} ${getCategoryIcon(cat as keyof ToolCategories)} ${cat}`
    )
  ];
  
  console.log(createBox('🎉 Configuration Summary', content));
  console.log('');
}

function getCategoryIcon(category: keyof ToolCategories): string {
  const icons: Record<keyof ToolCategories, string> = {
    basic: '🏥',
    rag: '🧠', 
    memory: '💭',
    agentManagement: '🤖',
    taskManagement: '📋',
    fileManagement: '📁',
    agentCommunication: '💬',
    sessionState: '💾',
    assistanceRequest: '🆘',
    backgroundAgents: '🎯'
  };
  return icons[category] || '🔧';
}

function getEstimatedToolCount(categories: ToolCategories): number {
  // Estimated tool counts based on actual implementations
  const toolCounts: Record<keyof ToolCategories, number> = {
    basic: 1,
    rag: 4,
    memory: 5,
    agentManagement: 8,
    taskManagement: 12,
    fileManagement: 3,
    agentCommunication: 3,
    sessionState: 2,
    assistanceRequest: 2,
    backgroundAgents: 3
  };
  
  return Object.entries(categories)
    .filter(([_, enabled]) => enabled)
    .reduce((total, [key, _]) => total + (toolCounts[key as keyof ToolCategories] || 0), 0);
}

console.log('✅ Enhanced TUI module loaded');