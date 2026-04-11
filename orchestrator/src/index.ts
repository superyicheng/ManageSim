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
   *
   * Routing logic:
   * - Explicit agentId → use that agent
   * - Sub-task (has parent_task) → route to assigned worker or best available worker
   * - Top-level task → route to the project's leader for analysis and delegation
   * - Fallback → highest success_rate agent
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

      let targetAgent;

      if (agentId) {
        // Explicit agent specified
        targetAgent = agents.find((a: any) => a.id === agentId);
      } else if (task.parent_task) {
        // Sub-task created by leader — route to assigned worker or best available worker
        if (task.assigned_to) {
          targetAgent = agents.find((a: any) => a.id === task.assigned_to);
        }
        if (!targetAgent) {
          targetAgent = agents
            .filter((a: any) => a.status === 'active' && a.role === 'worker')
            .sort((a: any, b: any) => (b.success_rate || 0) - (a.success_rate || 0))[0];
        }
      } else {
        // Top-level task — route to leader first for analysis and delegation
        targetAgent = agents.find(
          (a: any) => a.status === 'active' && a.role === 'leader'
        );
        if (!targetAgent) {
          // Fallback: pick by success rate (original behavior)
          targetAgent = agents
            .filter((a: any) => a.status === 'active')
            .sort((a: any, b: any) => (b.success_rate || 0) - (a.success_rate || 0))[0];
        }
      }

      if (!targetAgent) {
        return { error: 'No available agent for task dispatch' };
      }

      console.log(`[Orchestrator] Dispatching ${taskId} to ${targetAgent.id} (${targetAgent.role || 'unknown'})`);

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
        agent_role: targetAgent.role || 'unknown',
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
