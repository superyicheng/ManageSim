import { ManageSimConfig } from '../config-loader';
import axios from 'axios';

export class AssetTracker {
  private config: ManageSimConfig;

  constructor(config: ManageSimConfig) {
    this.config = config;
  }

  async trackTaskCompletion(taskId: string, projectId: string, summary: string): Promise<void> {
    try {
      await axios.post('http://localhost:8100/api/tasks', {
        id: taskId,
        project_id: projectId,
        title: summary,
        state: 'Done',
        completed_at: new Date().toISOString(),
      });
    } catch (error) {
      console.error('Failed to track task completion:', error);
    }
  }

  async trackAgentActivity(agentId: string, activity: string): Promise<void> {
    try {
      await axios.patch(`http://localhost:8100/api/agents/${agentId}`, {
        last_active: new Date().toISOString(),
      });
    } catch (error) {
      // Best-effort tracking
    }
  }
}
