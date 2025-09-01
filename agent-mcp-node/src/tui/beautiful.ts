// Beautiful TUI for Agent-MCP without animations
// Modern styling with fast performance - perfect for all terminals

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

// Enhanced color palette
const Colors = {
  ...TUIColors,
  ACCENT: '\x1b[38;5;208m',    // Orange accent
  SUCCESS: '\x1b[38;5;46m',    // Bright green
  INFO: '\x1b[38;5;117m',      // Sky blue
  SECONDARY: '\x1b[38;5;245m', // Gray
  PURPLE: '\x1b[38;5;141m',    // Light purple
} as const;

// Simple box drawing
const Box = {
  TOP_LEFT: '┌',
  TOP_RIGHT: '┐', 
  BOTTOM_LEFT: '└',
  BOTTOM_RIGHT: '┘',
  HORIZONTAL: '─',
  VERTICAL: '│',
  HEAVY_HORIZONTAL: '━',
  HEAVY_VERTICAL: '┃',
} as const;

function createSimpleBox(title: string, content: string[], width: number = 68): string {
  const lines: string[] = [];
  
  // Top border
  lines.push(`${Colors.INFO}${Box.TOP_LEFT}${Box.HEAVY_HORIZONTAL.repeat(width - 2)}${Box.TOP_RIGHT}${Colors.ENDC}`);
  
  // Title
  const titlePadding = Math.max(0, (width - title.length - 4) / 2);
  const titleLine = `${Colors.INFO}${Box.VERTICAL}${Colors.ENDC}${' '.repeat(Math.floor(titlePadding))}${Colors.BOLD}${Colors.ACCENT}${title}${Colors.ENDC}${' '.repeat(Math.ceil(titlePadding))}${Colors.INFO}${Box.VERTICAL}${Colors.ENDC}`;
  lines.push(titleLine);
  
  // Separator  
  lines.push(`${Colors.INFO}${Box.VERTICAL}${Box.HORIZONTAL.repeat(width - 2)}${Box.VERTICAL}${Colors.ENDC}`);
  
  // Content
  content.forEach(line => {
    const cleanLine = line.replace(/\x1b\[[0-9;]*m/g, '');
    const padding = Math.max(0, width - cleanLine.length - 4);
    lines.push(`${Colors.INFO}${Box.VERTICAL}${Colors.ENDC} ${line}${' '.repeat(padding)} ${Colors.INFO}${Box.VERTICAL}${Colors.ENDC}`);
  });
  
  // Bottom border
  lines.push(`${Colors.INFO}${Box.BOTTOM_LEFT}${Box.HEAVY_HORIZONTAL.repeat(width - 2)}${Box.BOTTOM_RIGHT}${Colors.ENDC}`);
  
  return lines.join('\n');
}

function createProgressBar(current: number, total: number, width: number = 30): string {
  const filled = Math.round((current / total) * width);
  const empty = width - filled;
  const percentage = Math.round((current / total) * 100);
  
  return `${Colors.ACCENT}[${'█'.repeat(filled)}${Colors.SECONDARY}${'░'.repeat(empty)}${Colors.ACCENT}] ${percentage}%${Colors.ENDC}`;
}

export async function launchBeautifulPreConfigurationTUI(): Promise<ToolCategories> {
  console.clear();
  
  displayBeautifulWelcomeBanner();
  
  const currentConfig = loadToolConfig();
  const currentMode = getConfigMode(currentConfig);
  
  // Show current configuration
  if (currentMode || getEnabledCategories(currentConfig).length < Object.keys(DEFAULT_CONFIG).length) {
    displayCurrentConfiguration(currentConfig, currentMode);
  }

  // Main menu
  const mainChoice = await showMainMenu();
  let finalConfig: ToolCategories;

  switch (mainChoice.action) {
    case 'quickstart':
      finalConfig = await handleQuickStart();
      break;
    case 'predefined':
      finalConfig = await handlePredefinedModeSelection();
      break;
    case 'custom':
      finalConfig = await handleCustomConfiguration();
      break;
    case 'advanced':
      finalConfig = await handleAdvancedSetup();
      break;
    case 'current':
    default:
      finalConfig = currentConfig.basic !== undefined ? currentConfig : DEFAULT_CONFIG;
      break;
  }

  // Validation
  const validation = validateToolConfig(finalConfig);
  if (validation.warnings.length > 0) {
    await showValidationWarnings(validation.warnings);
  }

  // Save and display summary
  saveToolConfig(finalConfig, getConfigMode(finalConfig) || 'custom');
  displayConfigurationSummary(finalConfig);
  
  console.log(`${Colors.SUCCESS}🚀 Starting Agent-MCP server...${Colors.ENDC}\n`);
  
  return finalConfig;
}

function displayBeautifulWelcomeBanner(): void {
  const bannerContent = [
    '',
    `${Colors.PURPLE}🤖 Agent-MCP Configuration Wizard${Colors.ENDC} ${Colors.SECONDARY}v${VERSION}${Colors.ENDC}`,
    '',
    `${Colors.INFO}Configure your Multi-Agent Collaboration Platform${Colors.ENDC}`,
    `${Colors.SECONDARY}Customize tools, modes, and capabilities${Colors.ENDC}`,
    ''
  ];
  
  console.log(createSimpleBox('Welcome to Agent-MCP', bannerContent, 72));
  console.log('');
}

function displayCurrentConfiguration(config: ToolCategories, mode: string | null): void {
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
    content.push('', `${Colors.ACCENT}Description:${Colors.ENDC}`);
    content.push(`${PREDEFINED_MODES[mode].description}`);
  }
  
  console.log(createSimpleBox('📋 Current Configuration', content));
  console.log('');
}

async function showMainMenu(): Promise<any> {
  const menuItems = [
    {
      name: `${Colors.SUCCESS}🚀 Quick Start${Colors.ENDC} - Get started fast with recommended settings`,
      value: 'quickstart',
      short: 'Quick Start'
    },
    {
      name: `${Colors.INFO}🎯 Choose Mode${Colors.ENDC} - Select from optimized configurations`,
      value: 'predefined',
      short: 'Predefined Mode'
    },
    {
      name: `${Colors.ACCENT}🔧 Custom Build${Colors.ENDC} - Pick exactly which tools you want`,
      value: 'custom',
      short: 'Custom Config'
    },
    {
      name: `${Colors.PURPLE}📊 Advanced Setup${Colors.ENDC} - Detailed configuration options`,
      value: 'advanced',
      short: 'Advanced Setup'
    },
    new inquirer.Separator(`${Colors.SECONDARY}────────────────────────────────────────────────${Colors.ENDC}`),
    {
      name: `${Colors.SECONDARY}✅ Use Current${Colors.ENDC} - Continue with existing settings`,
      value: 'current',
      short: 'Use Current'
    }
  ];

  return inquirer.prompt({
    type: 'list',
    name: 'action',
    message: `${Colors.BOLD}How would you like to configure Agent-MCP?${Colors.ENDC}`,
    choices: menuItems,
    pageSize: 10
  });
}

async function handleQuickStart(): Promise<ToolCategories> {
  console.clear();
  
  const content = [
    `${Colors.INFO}Perfect for getting started quickly!${Colors.ENDC}`,
    '',
    `${Colors.SUCCESS}🎯 Memory + RAG Mode${Colors.ENDC} (Recommended)`,
    '  • Code assistance and knowledge work',
    '  • Vector search and context memory',  
    '  • Lightweight and fast (~15 tools)',
    '',
    `${Colors.ACCENT}🔥 Full Mode${Colors.ENDC} - Complete platform`,
    `${Colors.SECONDARY}⚡ Minimal Mode${Colors.ENDC} - Basic only`,
    `${Colors.INFO}🎯 Background Agents${Colors.ENDC} - Standalone mode`,
  ];
  
  console.log(createSimpleBox('🚀 Quick Start Options', content));
  console.log('');

  const choice = await inquirer.prompt({
    type: 'list',
    name: 'mode',
    message: `${Colors.BOLD}Select your quick start option:${Colors.ENDC}`,
    choices: [
      {
        name: `${Colors.SUCCESS}🎯 Memory + RAG Mode${Colors.ENDC} (Recommended)`,
        value: 'memoryRag',
        short: 'Memory + RAG'
      },
      {
        name: `${Colors.ACCENT}🔥 Full Mode${Colors.ENDC} (All features)`,
        value: 'full', 
        short: 'Full Mode'
      },
      {
        name: `${Colors.SECONDARY}⚡ Minimal Mode${Colors.ENDC} (Fastest)`,
        value: 'minimal',
        short: 'Minimal'
      },
      {
        name: `${Colors.INFO}🎯 Background Agents${Colors.ENDC} (Standalone)`,
        value: 'background',
        short: 'Background'
      }
    ]
  });

  const selectedMode = PREDEFINED_MODES[choice.mode];
  if (!selectedMode) {
    throw new Error(`Invalid mode selection: ${choice.mode}`);
  }

  console.log(`${Colors.SUCCESS}✅ Quick start configured: ${selectedMode.name}${Colors.ENDC}\n`);
  return selectedMode.categories;
}

async function handlePredefinedModeSelection(): Promise<ToolCategories> {
  console.clear();
  
  const modeChoices = Object.entries(PREDEFINED_MODES).map(([key, mode]) => {
    const toolCount = Object.values(mode.categories).filter(Boolean).length;
    const totalCategories = Object.keys(mode.categories).length;
    
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

  const content = [
    'Choose from carefully optimized configurations:',
    '',
    `${Colors.SUCCESS}●${Colors.ENDC} Lightweight • ${Colors.INFO}●${Colors.ENDC} Balanced • ${Colors.ACCENT}●${Colors.ENDC} Feature-rich`
  ];

  console.log(createSimpleBox('🎯 Predefined Modes', content));
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

  console.log(`${Colors.SUCCESS}✅ Selected: ${selectedMode.name}${Colors.ENDC}\n`);
  return selectedMode.categories;
}

async function handleCustomConfiguration(): Promise<ToolCategories> {
  console.clear();
  
  const content = [
    'Build your perfect configuration by selecting the tools you need.',
    '',
    `${Colors.SECONDARY}Basic tools are always included for system health.${Colors.ENDC}`,
    `${Colors.INFO}Use SPACE to select/deselect, ENTER to confirm${Colors.ENDC}`
  ];

  console.log(createSimpleBox('🔧 Custom Configuration', content));
  console.log('');

  const categories = Object.entries(DEFAULT_CONFIG)
    .filter(([key]) => key !== 'basic')
    .map(([key, _]) => {
      const description = getCategoryDescription(key as keyof ToolCategories);
      const icon = getCategoryIcon(key as keyof ToolCategories);
      return {
        name: `${icon} ${Colors.BOLD}${key}${Colors.ENDC} - ${description}`,
        value: key,
        checked: false
      };
    });

  const selectedCategories = await inquirer.prompt({
    type: 'checkbox',
    name: 'categories',
    message: `${Colors.BOLD}Select the tool categories to enable:${Colors.ENDC}`,
    choices: categories,
    pageSize: 12,
    validate: (selections: any) => {
      if (selections.length === 0) {
        return 'Please select at least one category';
      }
      return true;
    }
  });

  const newConfig: ToolCategories = {
    basic: true,
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

  console.log(`${Colors.SUCCESS}✅ Custom configuration created${Colors.ENDC}\n`);
  return newConfig;
}

async function handleAdvancedSetup(): Promise<ToolCategories> {
  console.clear();
  
  const content = [
    'Walk through each tool category with detailed explanations.',
    'Get complete control over your Agent-MCP setup.',
    '',
    `${Colors.INFO}Dependencies will be suggested when needed.${Colors.ENDC}`
  ];

  console.log(createSimpleBox('📊 Advanced Setup', content));
  console.log('');
  
  // Implementation similar to enhanced but without animations
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
  
  // Simplified advanced setup - could be expanded
  console.log(`${Colors.INFO}Advanced setup would walk through each category...${Colors.ENDC}`);
  console.log(`${Colors.ACCENT}For now, falling back to custom configuration.${Colors.ENDC}\n`);
  
  return handleCustomConfiguration();
}

async function showValidationWarnings(warnings: string[]): Promise<void> {
  if (warnings.length === 0) return;
  
  const content = warnings.map(warning => `${Colors.WARNING}⚠${Colors.ENDC} ${warning}`);
  console.log(createSimpleBox('⚠️ Configuration Warnings', content));
  
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

function displayConfigurationSummary(config: ToolCategories): void {
  const enabledCategories = getEnabledCategories(config);
  const mode = getConfigMode(config);
  const totalCategories = Object.keys(config).length;
  
  const content = [
    mode && PREDEFINED_MODES[mode] 
      ? `${Colors.SUCCESS}Mode:${Colors.ENDC} ${PREDEFINED_MODES[mode].name}`
      : `${Colors.ACCENT}Mode:${Colors.ENDC} Custom Configuration`,
    '',
    `${Colors.INFO}Categories:${Colors.ENDC} ${createProgressBar(enabledCategories.length, totalCategories)}`,
    '',
    ...enabledCategories.map(cat => 
      `${Colors.SUCCESS}✓${Colors.ENDC} ${getCategoryIcon(cat as keyof ToolCategories)} ${cat}`
    )
  ];
  
  console.log(createSimpleBox('🎉 Configuration Complete', content));
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

console.log('✅ Beautiful TUI module loaded');