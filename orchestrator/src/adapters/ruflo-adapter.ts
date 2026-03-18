/**
 * Ruflo (Claude Flow) adapter — swarm execution dispatch.
 *
 * Ruflo provides multi-agent coordination with queen-worker topology
 * and SONA self-learning. This adapter bridges ManageSim tasks to
 * Ruflo swarm execution.
 */

import axios from 'axios';

interface SwarmConfig {
  queenAgentId: string;
  workerAgentIds: string[];
  maxConcurrent: number;
  consensusThreshold: number;
}

interface SwarmResult {
  status: string;
  outputs: any[];
  cost: number;
  tokensUsed: number;
}

export class RufloAdapter {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.RUFLO_URL || 'http://localhost:8200';
  }

  /**
   * Create a swarm execution for a task.
   */
  async createSwarm(
    taskId: string,
    config: SwarmConfig,
    instructions: string,
  ): Promise<any> {
    try {
      const response = await axios.post(`${this.baseUrl}/api/swarms`, {
        task_id: taskId,
        queen: config.queenAgentId,
        workers: config.workerAgentIds,
        max_concurrent: config.maxConcurrent,
        consensus_threshold: config.consensusThreshold,
        instructions,
      });
      return response.data;
    } catch (error: any) {
      console.error(`[Ruflo] Failed to create swarm: ${error.message}`);
      return { error: error.message };
    }
  }

  /**
   * Get swarm execution status.
   */
  async getSwarmStatus(swarmId: string): Promise<any> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/swarms/${swarmId}`);
      return response.data;
    } catch (error: any) {
      return { error: error.message };
    }
  }

  /**
   * Stop a running swarm.
   */
  async stopSwarm(swarmId: string): Promise<any> {
    try {
      const response = await axios.delete(`${this.baseUrl}/api/swarms/${swarmId}`);
      return response.data;
    } catch (error: any) {
      return { error: error.message };
    }
  }
}
