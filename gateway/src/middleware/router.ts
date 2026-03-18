import { Message } from 'discord.js';
import { ManageSimConfig, ProjectConfig } from '../config-loader';

export class MessageRouter {
  private config: ManageSimConfig;
  private channelToProject: Map<string, ProjectConfig>;

  constructor(config: ManageSimConfig) {
    this.config = config;
    this.channelToProject = new Map();
    for (const project of config.projects) {
      this.channelToProject.set(project.discord_channel_id, project);
    }
  }

  getProject(channelId: string): ProjectConfig | undefined {
    return this.channelToProject.get(channelId);
  }

  isAssetBaseChannel(channelId: string): boolean {
    return channelId === this.config.asset_base.channel_id;
  }

  routeMessage(msg: Message): { target: string; project?: ProjectConfig } {
    const channelId = msg.channel.id;

    if (this.isAssetBaseChannel(channelId)) {
      return { target: 'asset-base' };
    }

    const project = this.getProject(channelId);
    if (project) {
      return { target: 'project', project };
    }

    return { target: 'general' };
  }
}
