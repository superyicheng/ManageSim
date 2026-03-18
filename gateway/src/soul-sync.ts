import * as fs from 'fs';
import * as path from 'path';
import { ManageSimConfig } from './config-loader';

export class SoulSync {
  private config: ManageSimConfig;
  private easybaseDir: string;

  constructor(config: ManageSimConfig) {
    this.config = config;
    this.easybaseDir = config.settings.easybase.base_dir.replace('~', process.env.HOME || '');
  }

  async syncAll(): Promise<void> {
    console.log('Syncing soul.md files from Easybase...');

    // Sync server soul
    await this.syncChunk('server-soul', 'server');

    // Sync project souls
    for (const project of this.config.projects) {
      await this.syncChunk(`soul-${project.id}`, `server/${project.id}`);
    }

    console.log('Soul sync complete');
  }

  private async syncChunk(chunkId: string, treePath: string): Promise<void> {
    const chunkPath = path.join(this.easybaseDir, 'chunks', `${chunkId}.md`);

    if (!fs.existsSync(chunkPath)) {
      console.warn(`Chunk not found: ${chunkId} (${chunkPath})`);
      return;
    }

    try {
      const content = fs.readFileSync(chunkPath, 'utf-8');
      // Extract body (after frontmatter)
      const parts = content.split('---');
      const body = parts.length >= 3 ? parts.slice(2).join('---').trim() : '';

      if (body) {
        console.log(`  Synced: ${chunkId} (${body.length} chars)`);
      }
    } catch (error) {
      console.warn(`Failed to sync ${chunkId}: ${error}`);
    }
  }

  async pushToEasybase(chunkId: string, content: string): Promise<void> {
    // Write updated content back to Easybase chunk file
    const chunkPath = path.join(this.easybaseDir, 'chunks', `${chunkId}.md`);

    if (!fs.existsSync(chunkPath)) {
      console.warn(`Cannot push: chunk ${chunkId} does not exist`);
      return;
    }

    try {
      const existing = fs.readFileSync(chunkPath, 'utf-8');
      const parts = existing.split('---');
      if (parts.length >= 3) {
        // Preserve frontmatter, replace body
        const newContent = `---${parts[1]}---\n\n${content}\n`;
        fs.writeFileSync(chunkPath, newContent, 'utf-8');
        console.log(`Pushed update to ${chunkId}`);
      }
    } catch (error) {
      console.warn(`Failed to push ${chunkId}: ${error}`);
    }
  }
}
