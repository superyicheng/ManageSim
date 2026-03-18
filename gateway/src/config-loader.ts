import * as fs from 'fs';
import * as yaml from 'yaml';

export interface ProjectConfig {
  id: string;
  name: string;
  discord_channel_id: string;
  bot_token_env: string;
  team_template: string;
  pipeline: string;
  soul_template: string;
  stall_threshold_seconds: number;
}

export interface ManageSimConfig {
  version: string;
  discord: {
    guild_id: string;
  };
  settings: {
    easybase: { base_dir: string; auto_record: boolean };
    mem0: { storage: string; local_path: string };
    default_llm: string;
    default_visibility: string;
  };
  server: {
    name: string;
    soul_template: string;
    claude_template: string | null;
  };
  personal_assistant: {
    bot_token_env: string;
    name: string;
    channels: string;
    capabilities: string[];
  };
  projects: ProjectConfig[];
  asset_base: {
    bot_token_env: string;
    channel_id: string;
    storage_path: string;
  };
}

export function loadConfig(configPath: string): ManageSimConfig | null {
  try {
    const content = fs.readFileSync(configPath, 'utf-8');
    const config = yaml.parse(content) as ManageSimConfig;
    validateConfig(config);
    return config;
  } catch (error) {
    console.error(`Error loading config: ${error}`);
    return null;
  }
}

function validateConfig(config: ManageSimConfig): void {
  if (!config.version) throw new Error('Missing version');
  if (!config.discord?.guild_id) throw new Error('Missing discord.guild_id');
  if (!config.server?.name) throw new Error('Missing server.name');
  if (!config.personal_assistant?.bot_token_env) {
    throw new Error('Missing personal_assistant.bot_token_env');
  }
  for (const project of config.projects || []) {
    if (!project.id) throw new Error('Project missing id');
    if (!project.bot_token_env) throw new Error(`Project ${project.id} missing bot_token_env`);
  }
}
