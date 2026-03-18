/**
 * ManageSim Orchestrator — Paperclip + Ruflo bridge.
 *
 * Maps the 4-level hierarchy to Paperclip's company structure:
 *   Server = Company, Department = Division, Team = Bot, Agent = Worker
 *
 * Routes task execution through Ruflo (Claude Flow) swarm topology.
 */

import * as dotenv from 'dotenv';
import axios from 'axios';

dotenv.config();

const ASSET_BASE_URL = process.env.ASSET_BASE_URL || 'http://localhost:8100';

interface OrchestratorConfig {
  assetBaseUrl: string;
  defaultLlm: string;
}

class Orchestrator {
  private config: OrchestratorConfig;

  constructor(config?: Partial<OrchestratorConfig>) {
    this.config = {
      assetBaseUrl: config?.assetBaseUrl || ASSET_BASE_URL,
      defaultLlm: config?.defaultLlm || 'claude-sonnet-4-20250514',
    };
  }

  /**
   * Dispatch a task to the appropriate team/agent via the execution layer.
   */
  async dispatchTask(taskId: string, projectId: string, agentId?: string): Promise<any> {
    try {
      // Get task details
      const taskResponse = await axios.get(`${this.config.assetBaseUrl}/api/tasks/${taskId}`);
      const task = taskResponse.data;

      // Get available agents for the project
      const agentsResponse = await axios.get(`${this.config.assetBaseUrl}/api/agents`, {
        params: { project: projectId },
      });
      const agents = agentsResponse.data || [];

      // Select agent (specified or best match)
      let targetAgent;
      if (agentId) {
        targetAgent = agents.find((a: any) => a.id === agentId);
      } else {
        // Pick the active agent with highest success rate
        targetAgent = agents
          .filter((a: any) => a.status === 'active')
          .sort((a: any, b: any) => (b.success_rate || 0) - (a.success_rate || 0))[0];
      }

      if (!targetAgent) {
        return { error: 'No available agent for task dispatch' };
      }

      console.log(`[Orchestrator] Dispatching ${taskId} to ${targetAgent.id}`);

      // Update task assignment
      await axios.patch(`${this.config.assetBaseUrl}/api/tasks/${taskId}`, {
        assigned_to: targetAgent.id,
        state: 'Assigned',
      });

      return {
        status: 'dispatched',
        task_id: taskId,
        agent_id: targetAgent.id,
        agent_name: targetAgent.name,
      };
    } catch (error: any) {
      console.error(`[Orchestrator] Dispatch error: ${error.message}`);
      return { error: error.message };
    }
  }

  /**
   * Get the current status of all active tasks across projects.
   */
  async getSystemStatus(): Promise<any> {
    try {
      const [tasksRes, agentsRes] = await Promise.all([
        axios.get(`${this.config.assetBaseUrl}/api/tasks`, { params: { limit: 100 } }),
        axios.get(`${this.config.assetBaseUrl}/api/agents`),
      ]);

      const tasks = tasksRes.data || [];
      const agents = agentsRes.data || [];

      return {
        active_tasks: tasks.filter((t: any) => !['Done', 'Cancelled'].includes(t.state)).length,
        completed_tasks: tasks.filter((t: any) => t.state === 'Done').length,
        total_agents: agents.length,
        active_agents: agents.filter((a: any) => a.status === 'active').length,
      };
    } catch (error: any) {
      return { error: error.message };
    }
  }
}

async function main() {
  const orchestrator = new Orchestrator();

  console.log('[Orchestrator] Starting...');
  const status = await orchestrator.getSystemStatus();
  console.log('[Orchestrator] System status:', JSON.stringify(status, null, 2));

  // Keep alive — in production this would listen for events
  console.log('[Orchestrator] Ready. Waiting for dispatch requests...');
  setInterval(async () => {
    // Periodic health check
    const s = await orchestrator.getSystemStatus();
    if (s.error) {
      console.warn('[Orchestrator] Health check failed:', s.error);
    }
  }, 60000);
}

main().catch(console.error);

export { Orchestrator };
