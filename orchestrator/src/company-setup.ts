/**
 * Company setup — maps ManageSim config to Paperclip company structure.
 *
 * Hierarchy mapping:
 *   Server → Company
 *   Department (Channel) → Division
 *   Team (OpenClaw Bot) → Team
 *   Agent (Worker) → Employee
 */

import axios from 'axios';

const ASSET_BASE_URL = process.env.ASSET_BASE_URL || 'http://localhost:8100';

interface CompanyStructure {
  name: string;
  divisions: Division[];
}

interface Division {
  id: string;
  name: string;
  teams: TeamConfig[];
}

interface TeamConfig {
  id: string;
  name: string;
  agents: AgentConfig[];
}

interface AgentConfig {
  id: string;
  name: string;
  role: string;
}

export async function buildCompanyStructure(config: any): Promise<CompanyStructure> {
  const company: CompanyStructure = {
    name: config.server?.name || 'ManageSim',
    divisions: [],
  };

  for (const project of config.projects || []) {
    const division: Division = {
      id: project.id,
      name: project.name,
      teams: [],
    };

    // Fetch teams for this project
    try {
      const teamsRes = await axios.get(`${ASSET_BASE_URL}/api/teams`, {
        params: { project: project.id },
      });

      for (const team of teamsRes.data || []) {
        const teamConfig: TeamConfig = {
          id: team.id,
          name: team.name,
          agents: [],
        };

        // Fetch agents for this team
        try {
          const agentsRes = await axios.get(`${ASSET_BASE_URL}/api/agents`, {
            params: { team: team.id },
          });
          teamConfig.agents = (agentsRes.data || []).map((a: any) => ({
            id: a.id,
            name: a.name,
            role: a.role,
          }));
        } catch {
          // Continue without agents
        }

        division.teams.push(teamConfig);
      }
    } catch {
      // Continue without teams
    }

    company.divisions.push(division);
  }

  return company;
}

export function printStructure(company: CompanyStructure): string {
  const lines: string[] = [`Company: ${company.name}`];

  for (const div of company.divisions) {
    lines.push(`  Division: ${div.name} (${div.id})`);
    for (const team of div.teams) {
      lines.push(`    Team: ${team.name} (${team.id})`);
      for (const agent of team.agents) {
        lines.push(`      Agent: ${agent.name} [${agent.role}] (${agent.id})`);
      }
    }
  }

  return lines.join('\n');
}
