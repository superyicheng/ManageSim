import { Client, GatewayIntentBits, Message } from 'discord.js';
import { ManageSimConfig } from './config-loader';
import axios from 'axios';

export class PersonalAssistant {
  private client: Client;
  private config: ManageSimConfig;

  constructor(config: ManageSimConfig) {
    this.config = config;
    this.client = new Client({
      intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers,
      ],
    });

    this.client.on('ready', () => {
      console.log(`Personal assistant logged in as ${this.client.user?.tag}`);
    });

    this.client.on('messageCreate', (msg) => this.handleMessage(msg));
  }

  async start(): Promise<void> {
    const token = process.env[this.config.personal_assistant.bot_token_env];
    if (!token) {
      console.warn('No personal assistant token configured');
      return;
    }
    await this.client.login(token);
  }

  async stop(): Promise<void> {
    this.client.destroy();
  }

  private async handleMessage(msg: Message): Promise<void> {
    if (msg.author.bot) return;
    if (!this.isMentioned(msg)) return;

    const content = msg.content.replace(/<@!?\d+>/g, '').trim();

    // Handle department creation
    if (content.startsWith('create department')) {
      await this.handleCreateDepartment(msg, content);
      return;
    }

    // Handle asset queries
    if (content.startsWith('!tasks') || content.startsWith('!skills') || content.startsWith('!stats')) {
      await this.handleAssetQuery(msg, content);
      return;
    }

    // General QA — delegate to appropriate project bot or respond directly
    await this.handleGeneralQuery(msg, content);
  }

  private isMentioned(msg: Message): boolean {
    return msg.mentions.has(this.client.user!.id);
  }

  private async handleCreateDepartment(msg: Message, content: string): Promise<void> {
    const match = content.match(/create department\s+"([^"]+)"/i);
    if (!match) {
      await msg.reply('Usage: `@Assistant create department "Project Name"`');
      return;
    }

    const projectName = match[1];
    await msg.reply(`Creating department "${projectName}"... This will set up a new channel, bot, and Easybase tree.`);

    // Call the creators API
    try {
      const response = await axios.post('http://localhost:8100/api/departments', {
        name: projectName,
        guild_id: this.config.discord.guild_id,
      });
      await msg.reply(`Department created! Channel: ${response.data.channel_id}`);
    } catch (error) {
      await msg.reply('Department creation is handled via the setup scripts. Run `./scripts/init-personal.sh` to add a new project.');
    }
  }

  private async handleAssetQuery(msg: Message, content: string): Promise<void> {
    try {
      const baseUrl = 'http://localhost:8100';
      let response;

      if (content.startsWith('!tasks')) {
        const project = content.split(' ')[1] || '';
        response = await axios.get(`${baseUrl}/api/tasks`, {
          params: project ? { project } : {},
        });
        const tasks = response.data.slice(0, 5);
        const lines = tasks.map((t: any) => `\`${t.id}\` [${t.state}] ${t.title}`);
        await msg.reply(lines.join('\n') || 'No tasks found.');
      } else if (content.startsWith('!stats')) {
        response = await axios.get(`${baseUrl}/api/stats/server`);
        await msg.reply(`\`\`\`json\n${JSON.stringify(response.data, null, 2)}\n\`\`\``);
      }
    } catch (error) {
      await msg.reply('Could not reach Asset Base. Is it running?');
    }
  }

  private async handleGeneralQuery(msg: Message, content: string): Promise<void> {
    // Determine which project channel this is in
    const project = this.config.projects.find(
      (p) => p.discord_channel_id === msg.channel.id
    );

    if (project) {
      // Create a task from the user's message and route to the leader
      try {
        const baseUrl = 'http://localhost:8100';

        // Create the task via Asset Base
        const taskId = `${(project.id || project.name).toUpperCase().replace(/\s+/g, '-')}-${Date.now()}`;
        const taskResponse = await axios.post(`${baseUrl}/api/tasks`, {
          id: taskId,
          project_id: project.id || project.name,
          title: content.substring(0, 80),
          description: content,
          state: 'Inbox',
          pipeline: 'default',
          priority: 'normal',
        });

        // Find the leader agent for this project
        const agentsResponse = await axios.get(`${baseUrl}/api/agents`, {
          params: { project: project.id || project.name },
        });
        const agents = agentsResponse.data || [];
        const leader = agents.find((a: any) => a.role === 'leader' && a.status === 'active');

        if (leader) {
          await msg.reply(
            `Task created: \`${taskId}\`\nRouting to leader **${leader.name}** for analysis and delegation.`
          );
        } else {
          await msg.reply(
            `Task created: \`${taskId}\`\nNo leader found — task is in Inbox for manual triage.`
          );
        }
      } catch (error) {
        await msg.reply(
          `I received your request for ${project.name}. Could not create task — is the Asset Base running?`
        );
      }
    } else {
      await msg.reply('How can I help? Try `!tasks`, `!skills`, `!stats`, or `create department "Name"`. I work in all channels!');
    }
  }
}
