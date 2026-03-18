import { ManageSimConfig } from '../config-loader';

export interface AccessContext {
  requesterId: string;
  requesterProject: string;
  requesterTeam: string;
  requesterType: 'agent' | 'user';
}

export class AccessControl {
  private config: ManageSimConfig;

  constructor(config: ManageSimConfig) {
    this.config = config;
  }

  canAccess(chunk: any, context: AccessContext): boolean {
    const visibility = chunk.visibility || 'public';

    switch (visibility) {
      case 'public':
        return true;
      case 'project':
        return chunk.channel_origin === context.requesterProject;
      case 'team':
        return (chunk.tree_path || '').startsWith(
          `server/${context.requesterProject}/${context.requesterTeam}`
        );
      case 'agent':
        return chunk.stored_by === context.requesterId;
      case 'private':
        return context.requesterType === 'user';
      default:
        return true;
    }
  }

  filterChunks(chunks: any[], context: AccessContext): any[] {
    return chunks.filter((chunk) => this.canAccess(chunk, context));
  }
}
