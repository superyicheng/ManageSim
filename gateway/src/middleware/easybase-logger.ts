import { Message } from 'discord.js';
import { ManageSimConfig } from '../config-loader';
import axios from 'axios';

export class EasybaseLogger {
  private config: ManageSimConfig;

  constructor(config: ManageSimConfig) {
    this.config = config;
  }

  async logMessage(msg: Message, projectId: string): Promise<void> {
    if (!this.config.settings.easybase.auto_record) return;

    const record = {
      channel_id: msg.channel.id,
      author_id: msg.author.id,
      author_name: msg.author.username,
      content: msg.content.substring(0, 2000),
      timestamp: msg.createdAt.toISOString(),
      project_id: projectId,
    };

    try {
      // Log to Asset Base
      await axios.post('http://localhost:8100/api/tasks', {
        id: `msg-${msg.id}`,
        project_id: projectId,
        title: `Discord message from ${msg.author.username}`,
        description: msg.content.substring(0, 500),
        state: 'Done',
        tags: 'discord,message',
      });
    } catch (error) {
      // Logging is best-effort
    }
  }
}
