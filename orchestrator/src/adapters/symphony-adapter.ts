/**
 * Symphony adapter — autonomous task-to-PR lifecycle.
 *
 * Symphony uses OpenAI Codex for autonomous PR generation.
 * This adapter is a placeholder for Phase 3 (requires OpenAI key).
 */

import axios from 'axios';

export class SymphonyAdapter {
  private baseUrl: string;
  private available: boolean;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.SYMPHONY_URL || 'http://localhost:8300';
    this.available = !!process.env.OPENAI_API_KEY;
  }

  isAvailable(): boolean {
    return this.available;
  }

  /**
   * Submit a task for autonomous PR generation.
   */
  async submitTask(
    taskId: string,
    description: string,
    repoUrl: string,
  ): Promise<any> {
    if (!this.available) {
      return {
        error: 'Symphony requires OPENAI_API_KEY. Set it in .env to enable autonomous PRs.',
      };
    }

    try {
      const response = await axios.post(`${this.baseUrl}/api/tasks`, {
        task_id: taskId,
        description,
        repo_url: repoUrl,
      });
      return response.data;
    } catch (error: any) {
      return { error: error.message };
    }
  }

  /**
   * Get PR generation status.
   */
  async getStatus(taskId: string): Promise<any> {
    if (!this.available) {
      return { error: 'Symphony not available' };
    }

    try {
      const response = await axios.get(`${this.baseUrl}/api/tasks/${taskId}`);
      return response.data;
    } catch (error: any) {
      return { error: error.message };
    }
  }
}
