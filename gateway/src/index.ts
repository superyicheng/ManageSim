import * as dotenv from 'dotenv';
import { loadConfig, ManageSimConfig } from './config-loader';
import { PersonalAssistant } from './personal-assistant';
import { SoulSync } from './soul-sync';
import { EasybaseLogger } from './middleware/easybase-logger';
import { AssetTracker } from './middleware/asset-tracker';
import { AccessControl } from './middleware/access-control';
import { MessageRouter } from './middleware/router';

dotenv.config();

async function main() {
  console.log('ManageSim Gateway starting...');

  // Load configuration
  const configPath = process.env.MANAGESIM_CONFIG || './config/managesim.yaml';
  const config = loadConfig(configPath);

  if (!config) {
    console.error('Failed to load config from', configPath);
    process.exit(1);
  }

  console.log(`Loaded config: ${config.server.name}`);
  console.log(`Projects: ${config.projects.map(p => p.id).join(', ')}`);

  // Initialize middleware
  const logger = new EasybaseLogger(config);
  const tracker = new AssetTracker(config);
  const accessControl = new AccessControl(config);
  const router = new MessageRouter(config);

  // Initialize soul sync
  const soulSync = new SoulSync(config);

  // Start personal assistant
  const assistant = new PersonalAssistant(config);

  try {
    // Sync soul.md files from Easybase
    await soulSync.syncAll();

    // Start bots
    await assistant.start();
    console.log('Personal assistant started');

    // Start project bots
    for (const project of config.projects) {
      const token = process.env[project.bot_token_env];
      if (token) {
        console.log(`Starting bot for project: ${project.id}`);
        // Project bots would be started here via OpenClaw
      } else {
        console.warn(`No token for project ${project.id} (${project.bot_token_env})`);
      }
    }

    console.log('ManageSim Gateway ready!');
  } catch (error) {
    console.error('Failed to start gateway:', error);
    process.exit(1);
  }
}

main().catch(console.error);
