// Interactive TUI for real-time Agent-MCP configuration management
// Allows dynamic enabling/disabling of modes and tools while server runs

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
import { toolRegistry } from '../tools/registry.js';

interface InteractiveTUIOptions {
  serverRunning?: boolean;
  onConfigChange?: (config: ToolCategories) => Promise<void>;
  currentConfig?: ToolCategories;
}

export class InteractiveTUI {
  private config: ToolCategories;
  private serverRunning: boolean;
  private onConfigChange?: (config: ToolCategories) => Promise<void>;

  constructor(options: InteractiveTUIOptions = {}) {
    this.config = options.currentConfig || loadToolConfig();
    this.serverRunning = options.serverRunning || false;
    this.onConfigChange = options.onConfigChange;
  }

  async launch(): Promise<void> {
    console.clear();
    await this.showMainMenu();
  }

  private async showMainMenu(): Promise<void> {
    while (true) {
      console.clear();
      this.displayHeader();
      this.displayCurrentStatus();

      const choices = [
        {
          name: '🎯 Switch to Predefined Mode',
          value: 'predefined',
          short: 'Predefined Mode'
        },
        {
          name: '🔧 Toggle Individual Categories',
          value: 'categories',
          short: 'Toggle Categories'
        },
        {
          name: '🛠️  View/Toggle Specific Tools',
          value: 'tools',
          short: 'Toggle Tools'
        },
        {
          name: '📊 View Configuration Details',
          value: 'details',
          short: 'View Details'
        },
        {
          name: '💾 Save & Apply Configuration',
          value: 'apply',
          short: 'Save & Apply'
        },
        {
          name: '🔄 Reset to Default (Full Mode)',
          value: 'reset',
          short: 'Reset'
        },
        new inquirer.Separator(),
        {
          name: this.serverRunning ? '🚪 Exit TUI (Keep Server Running)' : '❌ Exit',
          value: 'exit',
          short: 'Exit'
        }
      ];

      const answer = await inquirer.prompt({
        type: 'list',
        name: 'action',
        message: 'What would you like to do?',
        choices,
        pageSize: 12
      });

      switch (answer.action) {
        case 'predefined':
          await this.handlePredefinedMode();
          break;
        case 'categories':
          await this.handleCategoryToggle();
          break;
        case 'tools':
          await this.handleToolView();
          break;
        case 'details':
          await this.handleDetailsView();
          break;
        case 'apply':
          await this.handleSaveAndApply();
          break;
        case 'reset':
          await this.handleReset();
          break;
        case 'exit':
          console.log(`${TUIColors.OKCYAN}👋 Goodbye!${TUIColors.ENDC}`);
          return;
      }
    }
  }

  private displayHeader(): void {
    console.log(`${TUIColors.HEADER}╔════════════════════════════════════════════════════════════╗${TUIColors.ENDC}`);
    console.log(`${TUIColors.HEADER}║                                                            ║${TUIColors.ENDC}`);
    console.log(`${TUIColors.HEADER}║        🎛️  Agent-MCP Interactive Configuration            ║${TUIColors.ENDC}`);
    console.log(`${TUIColors.HEADER}║                                                            ║${TUIColors.ENDC}`);
    console.log(`${TUIColors.HEADER}║      Toggle modes, categories, and tools in real-time     ║${TUIColors.ENDC}`);
    console.log(`${TUIColors.HEADER}║                                                            ║${TUIColors.ENDC}`);
    console.log(`${TUIColors.HEADER}╚════════════════════════════════════════════════════════════╝${TUIColors.ENDC}`);
    console.log('');
  }

  private displayCurrentStatus(): void {
    const currentMode = getConfigMode(this.config);
    const enabledCategories = getEnabledCategories(this.config);
    const totalTools = this.getToolCount();

    console.log(`${TUIColors.OKBLUE}📋 Current Configuration:${TUIColors.ENDC}`);
    
    if (currentMode && PREDEFINED_MODES[currentMode]) {
      console.log(`   Mode: ${TUIColors.OKGREEN}${PREDEFINED_MODES[currentMode].name}${TUIColors.ENDC}`);
    } else {
      console.log(`   Mode: ${TUIColors.WARNING}Custom Configuration${TUIColors.ENDC}`);
    }
    
    console.log(`   Categories: ${TUIColors.OKCYAN}${enabledCategories.length}/9 enabled${TUIColors.ENDC}`);
    console.log(`   Tools: ${TUIColors.OKGREEN}~${totalTools} available${TUIColors.ENDC}`);
    
    if (this.serverRunning) {
      console.log(`   Status: ${TUIColors.OKGREEN}🟢 Server Running${TUIColors.ENDC}`);
    } else {
      console.log(`   Status: ${TUIColors.DIM}⚫ Server Not Running${TUIColors.ENDC}`);
    }
    
    console.log(`   Enabled: ${TUIColors.OKGREEN}${enabledCategories.join(', ')}${TUIColors.ENDC}`);
    
    const disabledCategories = getDisabledCategories(this.config);
    if (disabledCategories.length > 0) {
      console.log(`   Disabled: ${TUIColors.DIM}${disabledCategories.join(', ')}${TUIColors.ENDC}`);
    }
    console.log('');
  }

  private async handlePredefinedMode(): Promise<void> {
    console.log(`${TUIColors.HEADER}🎯 Select Predefined Mode${TUIColors.ENDC}\n`);

    const choices = Object.entries(PREDEFINED_MODES).map(([key, mode]) => {
      const isCurrentMode = getConfigMode(this.config) === key;
      const prefix = isCurrentMode ? '✅ ' : '   ';
      
      return {
        name: `${prefix}${mode.name} - ${mode.description}`,
        value: key,
        short: mode.name
      };
    });

    const answer = await inquirer.prompt({
      type: 'list',
      name: 'mode',
      message: 'Choose a predefined mode:',
      choices: [
        ...choices,
        new inquirer.Separator(),
        { name: '← Back to Main Menu', value: 'back', short: 'Back' }
      ],
      pageSize: 10
    });

    if (answer.mode === 'back') return;

    const selectedMode = PREDEFINED_MODES[answer.mode];
    if (selectedMode) {
      this.config = { ...selectedMode.categories };
      console.log(`${TUIColors.OKGREEN}✅ Switched to ${selectedMode.name}${TUIColors.ENDC}`);
      
      const applyNow = await inquirer.prompt({
        type: 'confirm',
        name: 'apply',
        message: 'Apply this configuration now?',
        default: true
      });

      if (applyNow.apply) {
        await this.applyConfiguration();
      }
    }

    await this.pressEnterToContinue();
  }

  private async handleCategoryToggle(): Promise<void> {
    console.log(`${TUIColors.HEADER}🔧 Toggle Tool Categories${TUIColors.ENDC}\n`);

    const categories = Object.entries(this.config)
      .filter(([key]) => key !== 'basic') // Basic is always enabled
      .map(([key, enabled]) => ({
        name: `${enabled ? '✅' : '❌'} ${key} - ${getCategoryDescription(key as keyof ToolCategories)}`,
        value: key,
        checked: enabled
      }));

    const answer = await inquirer.prompt({
      type: 'checkbox',
      name: 'categories',
      message: 'Select categories to enable (basic is always enabled):',
      choices: categories,
      pageSize: 15
    });

    // Update configuration
    const newConfig: ToolCategories = {
      basic: true, // Always enabled
      rag: answer.categories.includes('rag'),
      memory: answer.categories.includes('memory'),
      agentManagement: answer.categories.includes('agentManagement'),
      taskManagement: answer.categories.includes('taskManagement'),
      fileManagement: answer.categories.includes('fileManagement'),
      agentCommunication: answer.categories.includes('agentCommunication'),
      sessionState: answer.categories.includes('sessionState'),
      assistanceRequest: answer.categories.includes('assistanceRequest'),
      backgroundAgents: answer.categories.includes('backgroundAgents')
    };

    this.config = newConfig;

    // Show what changed
    const validation = validateToolConfig(this.config);
    if (validation.warnings.length > 0) {
      console.log(`${TUIColors.WARNING}⚠️  Configuration warnings:${TUIColors.ENDC}`);
      validation.warnings.forEach(warning => console.log(`   • ${warning}`));
    }

    console.log(`${TUIColors.OKGREEN}✅ Categories updated${TUIColors.ENDC}`);

    const applyNow = await inquirer.prompt({
      type: 'confirm',
      name: 'apply',
      message: 'Apply these changes now?',
      default: true
    });

    if (applyNow.apply) {
      await this.applyConfiguration();
    }

    await this.pressEnterToContinue();
  }

  private async handleToolView(): Promise<void> {
    console.log(`${TUIColors.HEADER}🛠️  Available Tools by Category${TUIColors.ENDC}\n`);

    const toolsByCategory = this.getToolsByCategory();
    
    Object.entries(toolsByCategory).forEach(([category, tools]) => {
      const isEnabled = this.config[category as keyof ToolCategories];
      const statusIcon = isEnabled ? '✅' : '❌';
      const color = isEnabled ? TUIColors.OKGREEN : TUIColors.DIM;
      
      console.log(`${color}${statusIcon} ${category.toUpperCase()} (${tools.length} tools)${TUIColors.ENDC}`);
      tools.forEach(tool => {
        console.log(`   ${color}• ${tool}${TUIColors.ENDC}`);
      });
      console.log('');
    });

    await this.pressEnterToContinue();
  }

  private async handleDetailsView(): Promise<void> {
    console.log(`${TUIColors.HEADER}📊 Configuration Details${TUIColors.ENDC}\n`);

    const currentMode = getConfigMode(this.config);
    const enabledCategories = getEnabledCategories(this.config);
    const disabledCategories = getDisabledCategories(this.config);
    const estimatedTools = this.getToolCount();

    console.log(`${TUIColors.BOLD}Configuration Summary:${TUIColors.ENDC}`);
    console.log(`  Mode: ${currentMode && PREDEFINED_MODES[currentMode] ? 
      TUIColors.OKGREEN + PREDEFINED_MODES[currentMode].name : 
      TUIColors.WARNING + 'Custom'} ${TUIColors.ENDC}`);
    console.log(`  Enabled Categories: ${enabledCategories.length}/9`);
    console.log(`  Estimated Tools: ~${estimatedTools}`);
    console.log(`  Memory Usage: ${this.getMemoryEstimate()}`);
    console.log(`  Startup Time: ${this.getStartupEstimate()}`);
    console.log('');

    console.log(`${TUIColors.OKGREEN}✅ Enabled Categories:${TUIColors.ENDC}`);
    enabledCategories.forEach(category => {
      console.log(`  • ${category} - ${getCategoryDescription(category as keyof ToolCategories)}`);
    });
    console.log('');

    if (disabledCategories.length > 0) {
      console.log(`${TUIColors.DIM}❌ Disabled Categories:${TUIColors.ENDC}`);
      disabledCategories.forEach(category => {
        console.log(`  • ${TUIColors.DIM}${category} - ${getCategoryDescription(category as keyof ToolCategories)}${TUIColors.ENDC}`);
      });
      console.log('');
    }

    const validation = validateToolConfig(this.config);
    if (validation.warnings.length > 0) {
      console.log(`${TUIColors.WARNING}⚠️  Warnings:${TUIColors.ENDC}`);
      validation.warnings.forEach(warning => {
        console.log(`  • ${warning}`);
      });
      console.log('');
    }

    await this.pressEnterToContinue();
  }

  private async handleSaveAndApply(): Promise<void> {
    console.log(`${TUIColors.OKCYAN}💾 Saving and applying configuration...${TUIColors.ENDC}`);
    
    await this.applyConfiguration();
    
    console.log(`${TUIColors.OKGREEN}✅ Configuration applied successfully!${TUIColors.ENDC}`);
    
    if (this.serverRunning) {
      console.log(`${TUIColors.WARNING}⚠️  Note: Server restart may be required for all changes to take effect${TUIColors.ENDC}`);
    }

    await this.pressEnterToContinue();
  }

  private async handleReset(): Promise<void> {
    const confirm = await inquirer.prompt({
      type: 'confirm',
      name: 'reset',
      message: 'Reset to Full Mode (all tools enabled)?',
      default: false
    });

    if (confirm.reset) {
      this.config = { ...DEFAULT_CONFIG };
      console.log(`${TUIColors.OKGREEN}✅ Reset to Full Mode${TUIColors.ENDC}`);
      
      const applyNow = await inquirer.prompt({
        type: 'confirm',
        name: 'apply',
        message: 'Apply reset configuration now?',
        default: true
      });

      if (applyNow.apply) {
        await this.applyConfiguration();
      }
    }

    await this.pressEnterToContinue();
  }

  private async applyConfiguration(): Promise<void> {
    try {
      const currentMode = getConfigMode(this.config);
      saveToolConfig(this.config, currentMode || undefined);
      
      if (this.onConfigChange) {
        await this.onConfigChange(this.config);
      }
    } catch (error) {
      console.log(`${TUIColors.FAIL}❌ Failed to apply configuration: ${error instanceof Error ? error.message : error}${TUIColors.ENDC}`);
    }
  }

  private getToolCount(): number {
    // Estimate based on typical tool counts per category
    const toolCounts = {
      basic: 1,
      rag: 2,
      memory: 6,
      agentManagement: 7,
      taskManagement: 6,
      fileManagement: 2,
      agentCommunication: 3,
      sessionState: 4,
      assistanceRequest: 1
    };

    return Object.entries(this.config)
      .filter(([_, enabled]) => enabled)
      .reduce((total, [category, _]) => {
        return total + (toolCounts[category as keyof typeof toolCounts] || 0);
      }, 0);
  }

  private getToolsByCategory(): Record<string, string[]> {
    // This would ideally come from the tool registry, but for now we'll use static data
    return {
      basic: ['health'],
      rag: ['ask_project_rag', 'get_rag_status'],
      memory: ['view_project_context', 'update_project_context', 'bulk_update_project_context', 'delete_project_context', 'backup_project_context', 'validate_context_consistency'],
      agentManagement: ['create_agent', 'view_status', 'terminate_agent', 'list_agents', 'relaunch_agent', 'audit_agent_sessions', 'smart_audit_agents'],
      taskManagement: ['create_self_task', 'assign_task', 'view_tasks', 'update_task_status', 'search_tasks', 'delete_task'],
      fileManagement: ['check_file_status', 'update_file_status'],
      agentCommunication: ['send_agent_message', 'get_agent_messages', 'broadcast_admin_message'],
      sessionState: ['save_session_state', 'load_session_state', 'list_session_states', 'clear_session_state'],
      assistanceRequest: ['request_assistance']
    };
  }

  private getMemoryEstimate(): string {
    const enabledCount = getEnabledCategories(this.config).length;
    const baseMemory = 50;
    const categoryMemory = enabledCount * 12;
    return `~${baseMemory + categoryMemory}MB`;
  }

  private getStartupEstimate(): string {
    const enabledCount = getEnabledCategories(this.config).length;
    if (enabledCount <= 2) return 'Fast (~2s)';
    if (enabledCount <= 5) return 'Medium (~4s)';
    return 'Full (~6s)';
  }

  private async pressEnterToContinue(): Promise<void> {
    await inquirer.prompt({
      type: 'input',
      name: 'continue',
      message: 'Press Enter to continue...',
      filter: () => true
    });
  }
}

export async function launchInteractiveTUI(options: InteractiveTUIOptions = {}): Promise<void> {
  const tui = new InteractiveTUI(options);
  await tui.launch();
}