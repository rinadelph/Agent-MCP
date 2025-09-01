// Main TUI launcher for Agent-MCP tool configuration
// Interactive configuration interface for selecting tool categories and modes

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
import { TUIColors } from '../core/config.js';

export interface TUIOptions {
  currentConfig?: ToolCategories;
  skipSave?: boolean;
  showAdvanced?: boolean;
}

export async function launchConfigurationTUI(options: TUIOptions = {}): Promise<ToolCategories> {
  console.clear();
  displayBanner();
  
  const currentConfig = options.currentConfig || loadToolConfig();
  const currentMode = getConfigMode(currentConfig);
  
  console.log(`${TUIColors.OKBLUE}📊 Current Configuration:${TUIColors.ENDC}`);
  if (currentMode && PREDEFINED_MODES[currentMode]) {
    console.log(`   Mode: ${TUIColors.OKGREEN}${PREDEFINED_MODES[currentMode].name}${TUIColors.ENDC}`);
    console.log(`   ${PREDEFINED_MODES[currentMode].description}`);
  } else {
    console.log(`   Mode: ${TUIColors.WARNING}Custom Configuration${TUIColors.ENDC}`);
  }
  
  const enabledCategories = getEnabledCategories(currentConfig);
  const disabledCategories = getDisabledCategories(currentConfig);
  
  console.log(`   Enabled: ${TUIColors.OKGREEN}${enabledCategories.join(', ')}${TUIColors.ENDC}`);
  if (disabledCategories.length > 0) {
    console.log(`   Disabled: ${TUIColors.DIM}${disabledCategories.join(', ')}${TUIColors.ENDC}`);
  }
  console.log('');
  
  // Main configuration menu
  const mainChoice = await inquirer.prompt({
    type: 'list',
    name: 'action',
    message: 'How would you like to configure Agent-MCP?',
    choices: [
      {
        name: '🚀 Use Predefined Mode - Quick setup with common configurations',
        value: 'predefined'
      },
      {
        name: '🔧 Custom Configuration - Select individual tool categories',
        value: 'custom'
      },
      {
        name: '👀 Review Current Configuration - View detailed settings',
        value: 'review'
      },
      {
        name: '✅ Use Current Configuration - Continue with existing settings',
        value: 'continue'
      },
      {
        name: '🔄 Reset to Default - Restore full mode configuration',
        value: 'reset'
      }
    ]
  });
  
  let finalConfig: ToolCategories;
  
  switch (mainChoice.action) {
    case 'predefined':
      finalConfig = await selectPredefinedMode();
      break;
      
    case 'custom':
      finalConfig = await customConfiguration(currentConfig);
      break;
      
    case 'review':
      await reviewConfiguration(currentConfig);
      return await launchConfigurationTUI({ ...options, currentConfig }); // Return to main menu
      
    case 'reset':
      finalConfig = PREDEFINED_MODES.full?.categories || DEFAULT_CONFIG;
      console.log(`${TUIColors.OKGREEN}✅ Configuration reset to Full Mode${TUIColors.ENDC}`);
      break;
      
    case 'continue':
    default:
      finalConfig = currentConfig;
      console.log(`${TUIColors.OKGREEN}✅ Using current configuration${TUIColors.ENDC}`);
      break;
  }
  
  // Validate configuration
  const validation = validateToolConfig(finalConfig);
  if (validation.warnings.length > 0) {
    console.log(`${TUIColors.WARNING}⚠️  Configuration Warnings:${TUIColors.ENDC}`);
    validation.warnings.forEach(warning => {
      console.log(`   • ${warning}`);
    });
    console.log('');
    
    const confirmWarnings = await inquirer.prompt({
      type: 'confirm',
      name: 'proceed',
      message: 'Continue with this configuration despite warnings?',
      default: true
    });
    
    if (!confirmWarnings.proceed) {
      console.log(`${TUIColors.DIM}Returning to configuration menu...${TUIColors.ENDC}`);
      return await launchConfigurationTUI({ ...options, currentConfig: finalConfig });
    }
  }
  
  // Save configuration unless skipped
  if (!options.skipSave) {
    try {
      const selectedMode = getConfigMode(finalConfig);
      saveToolConfig(finalConfig, selectedMode || undefined);
      console.log(`${TUIColors.OKGREEN}💾 Configuration saved successfully${TUIColors.ENDC}`);
    } catch (error) {
      console.log(`${TUIColors.FAIL}❌ Failed to save configuration: ${error instanceof Error ? error.message : error}${TUIColors.ENDC}`);
      console.log(`${TUIColors.DIM}Configuration will be used for this session only${TUIColors.ENDC}`);
    }
  }
  
  return finalConfig;
}

async function selectPredefinedMode(): Promise<ToolCategories> {
  console.log(`${TUIColors.HEADER}🎯 Select Predefined Mode${TUIColors.ENDC}\n`);
  
  const choices = Object.entries(PREDEFINED_MODES).map(([key, mode]) => ({
    name: `${mode.name} - ${mode.description}`,
    value: key,
    short: mode.name
  }));
  
  const modeChoice = await inquirer.prompt({
    type: 'list',
    name: 'mode',
    message: 'Choose a predefined mode:',
    choices,
    pageSize: 10
  });
  
  const selectedMode = PREDEFINED_MODES[modeChoice.mode];
  if (!selectedMode) {
    throw new Error(`Invalid mode selection: ${modeChoice.mode}`);
  }
  console.log(`${TUIColors.OKGREEN}✅ Selected: ${selectedMode.name}${TUIColors.ENDC}`);
  
  return selectedMode.categories;
}

async function customConfiguration(currentConfig: ToolCategories): Promise<ToolCategories> {
  console.log(`${TUIColors.HEADER}🔧 Custom Tool Configuration${TUIColors.ENDC}\n`);
  
  const categories = Object.entries(currentConfig)
    .filter(([key]) => key !== 'basic') // Basic tools are always enabled
    .map(([key, enabled]) => ({
      name: `${key} - ${getCategoryDescription(key as keyof ToolCategories)}`,
      value: key,
      checked: enabled
    }));
  
  const selectedCategories = await inquirer.prompt({
    type: 'checkbox',
    name: 'categories',
    message: 'Select tool categories to enable:',
    choices: categories,
    pageSize: 15,
    validate: (selections) => {
      if (selections.length === 0) {
        return 'Please select at least one category (basic tools are always enabled)';
      }
      return true;
    }
  });
  
  // Build new configuration
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
  
  console.log(`${TUIColors.OKGREEN}✅ Custom configuration created${TUIColors.ENDC}`);
  
  return newConfig;
}

async function reviewConfiguration(config: ToolCategories): Promise<void> {
  console.log(`${TUIColors.HEADER}📋 Configuration Review${TUIColors.ENDC}\n`);
  
  const currentMode = getConfigMode(config);
  if (currentMode && PREDEFINED_MODES[currentMode]) {
    console.log(`${TUIColors.OKBLUE}Mode: ${PREDEFINED_MODES[currentMode].name}${TUIColors.ENDC}`);
    console.log(`${PREDEFINED_MODES[currentMode].description}\n`);
  } else {
    console.log(`${TUIColors.WARNING}Mode: Custom Configuration${TUIColors.ENDC}\n`);
  }
  
  console.log(`${TUIColors.BOLD}Tool Categories:${TUIColors.ENDC}`);
  
  Object.entries(config).forEach(([category, enabled]) => {
    const status = enabled ? 
      `${TUIColors.OKGREEN}✅ Enabled${TUIColors.ENDC}` : 
      `${TUIColors.DIM}❌ Disabled${TUIColors.ENDC}`;
    
    const description = getCategoryDescription(category as keyof ToolCategories);
    console.log(`  ${category.padEnd(20)} ${status}`);
    console.log(`    ${TUIColors.DIM}${description}${TUIColors.ENDC}`);
  });
  
  console.log('');
  
  // Show impact summary
  const enabledCount = Object.values(config).filter(Boolean).length;
  const totalCount = Object.values(config).length;
  
  console.log(`${TUIColors.OKBLUE}Summary:${TUIColors.ENDC}`);
  console.log(`  Enabled Categories: ${enabledCount}/${totalCount}`);
  console.log(`  Memory Usage: ${getMemoryEstimate(config)}`);
  console.log(`  Startup Time: ${getStartupEstimate(config)}`);
  
  await inquirer.prompt({
    type: 'input',
    name: 'continue',
    message: 'Press Enter to continue...',
    filter: () => true
  });
}

function getMemoryEstimate(config: ToolCategories): string {
  const enabledCategories = getEnabledCategories(config);
  const baseMemory = 50; // Base memory in MB
  const categoryMemory = {
    basic: 10,
    rag: 30,
    memory: 15,
    agentManagement: 25,
    taskManagement: 20,
    fileManagement: 10,
    agentCommunication: 15,
    sessionState: 10,
    assistanceRequest: 5
  };
  
  const totalMemory = enabledCategories.reduce((total, category) => {
    return total + (categoryMemory[category as keyof typeof categoryMemory] || 0);
  }, baseMemory);
  
  return `~${totalMemory}MB`;
}

function getStartupEstimate(config: ToolCategories): string {
  const enabledCount = getEnabledCategories(config).length;
  
  if (enabledCount <= 3) return 'Fast (~2s)';
  if (enabledCount <= 6) return 'Medium (~4s)';
  return 'Full (~6s)';
}

function displayBanner(): void {
  console.log(`${TUIColors.HEADER}╔══════════════════════════════════════════════════════════╗${TUIColors.ENDC}`);
  console.log(`${TUIColors.HEADER}║                                                          ║${TUIColors.ENDC}`);
  console.log(`${TUIColors.HEADER}║            🛠️  Agent-MCP Configuration Tool              ║${TUIColors.ENDC}`);
  console.log(`${TUIColors.HEADER}║                                                          ║${TUIColors.ENDC}`);
  console.log(`${TUIColors.HEADER}║   Configure which tools and features to enable          ║${TUIColors.ENDC}`);
  console.log(`${TUIColors.HEADER}║   Choose from predefined modes or create custom setup   ║${TUIColors.ENDC}`);
  console.log(`${TUIColors.HEADER}║                                                          ║${TUIColors.ENDC}`);
  console.log(`${TUIColors.HEADER}╚══════════════════════════════════════════════════════════╝${TUIColors.ENDC}`);
  console.log('');
}

export type { ToolCategories } from '../core/toolConfig.js';