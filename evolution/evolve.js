/**
 * ManageSim Agent Evolution Engine
 *
 * Inspired by Evolver's Genome Evolution Protocol (GEP).
 * Adapted for behavioral/prompt evolution instead of code modification.
 *
 * Cycle: SCAN → SIGNALS → SELECTION → MUTATION → VALIDATE → SOLIDIFY
 */

const fs = require('fs');
const path = require('path');
const axios = require('axios');
const { extractSignals } = require('./signal_extractor');
const { PersonalityState } = require('./personality');
const { solidifyBehavioral } = require('./solidify_behavioral');
const { shareCapsule } = require('./capsule_sharing');

const ASSET_BASE_URL = process.env.ASSET_BASE_URL || 'http://localhost:8100';
const EVOLUTION_INTERVAL_MS = parseInt(process.env.EVOLUTION_INTERVAL_MS || '3600000'); // 1 hour

class EvolutionEngine {
  constructor() {
    this.running = false;
  }

  async evolveAgent(agentId) {
    console.log(`[Evolution] Starting cycle for agent: ${agentId}`);

    try {
      // 1. SCAN — Read agent's recent activity
      const agentData = await this.scan(agentId);
      if (!agentData) {
        console.log(`[Evolution] No data for agent ${agentId}, skipping`);
        return null;
      }

      // 2. SIGNALS — Extract typed signals
      const signals = await this.extractSignals(agentData);
      console.log(`[Evolution] Found ${signals.length} signals for ${agentId}`);

      if (signals.length === 0) {
        // Stagnation check
        agentData._emptyCount = (agentData._emptyCount || 0) + 1;
        if (agentData._emptyCount >= 3) {
          signals.push({ type: 'stagnation', message: 'No signals for 3+ cycles' });
        } else {
          console.log(`[Evolution] No signals, skipping cycle`);
          return null;
        }
      }

      // 3. SELECTION — Score and rank genes
      const genes = await this.selectGenes(agentData, signals);
      console.log(`[Evolution] Selected ${genes.length} genes for mutation`);

      // 4. MUTATION — Create mutation record
      const mutation = await this.createMutation(agentData, genes, signals);
      if (!mutation) {
        console.log(`[Evolution] No mutation generated`);
        return null;
      }

      // 5. VALIDATE — Test the change
      const valid = await this.validate(agentData, mutation);
      if (!valid) {
        console.log(`[Evolution] Mutation failed validation, discarding`);
        return null;
      }

      // 6. SOLIDIFY — Commit changes
      const result = await this.solidify(agentData, mutation);
      console.log(`[Evolution] Solidified mutation for ${agentId}`);

      // Record evolution event
      await this.recordEvent(agentId, {
        signals: signals.length,
        genes: genes.map(g => g.id),
        mutation: mutation.description,
        result: 'success',
      });

      return result;

    } catch (error) {
      console.error(`[Evolution] Error evolving ${agentId}:`, error.message);
      await this.recordEvent(agentId, {
        error: error.message,
        result: 'failure',
      });
      return null;
    }
  }

  async scan(agentId) {
    try {
      const response = await axios.get(`${ASSET_BASE_URL}/api/agents/${agentId}`);
      const agent = response.data;

      // Get recent tasks
      const tasksResponse = await axios.get(`${ASSET_BASE_URL}/api/tasks`, {
        params: { project: agent.project_id, limit: 20 },
      });

      // Get error reports for this agent
      let errorReports = [];
      try {
        const errResponse = await axios.get(`${ASSET_BASE_URL}/api/error-reports`, {
          params: { agent: agentId },
        });
        errorReports = errResponse.data || [];
      } catch (e) {
        // Error reports endpoint may not exist yet
      }

      return {
        ...agent,
        recentTasks: tasksResponse.data || [],
        errorReports,
      };
    } catch (error) {
      return null;
    }
  }

  async extractSignals(agentData) {
    return extractSignals(agentData);
  }

  async selectGenes(agentData, signals) {
    const role = agentData.role || 'worker';
    const genesPath = path.join(__dirname, 'genes', `${role}_genes.json`);

    let genes = [];
    try {
      genes = JSON.parse(fs.readFileSync(genesPath, 'utf-8'));
    } catch (error) {
      console.warn(`[Evolution] No genes file for role: ${role}`);
      return [];
    }

    // Score genes by signal matching
    for (const gene of genes) {
      gene._score = 0;
      for (const signal of signals) {
        if (gene.signal_types && gene.signal_types.includes(signal.type)) {
          gene._score += 0.12;
        }
      }
      // Historical outcome boost
      const successRate = agentData.success_rate || 0;
      if (successRate > 0.8) gene._score += 0.05;
      if (successRate < 0.5) gene._score -= 0.05;
    }

    // Return top genes
    genes.sort((a, b) => b._score - a._score);
    return genes.filter(g => g._score > 0).slice(0, 3);
  }

  async createMutation(agentData, genes, signals) {
    if (genes.length === 0) return null;

    const topGene = genes[0];
    return {
      agent_id: agentData.id,
      gene_id: topGene.id,
      description: `Evolve ${topGene.name}: ${topGene.mutation_template || 'improve performance'}`,
      changes: {
        soul_additions: topGene.soul_additions || [],
        claude_additions: topGene.claude_additions || [],
        personality_adjustments: topGene.personality_adjustments || {},
      },
      signals_addressed: signals.map(s => s.type),
    };
  }

  async validate(agentData, mutation) {
    // Basic validation: ensure changes are reasonable
    const changes = mutation.changes;

    if (changes.personality_adjustments) {
      for (const [dim, delta] of Object.entries(changes.personality_adjustments)) {
        if (typeof delta === 'number' && Math.abs(delta) > 0.2) {
          return false; // Too large a personality shift
        }
      }
    }

    return true;
  }

  async solidify(agentData, mutation) {
    return solidifyBehavioral(agentData, mutation);
  }

  async recordEvent(agentId, event) {
    try {
      await axios.post(`${ASSET_BASE_URL}/api/tasks`, {
        id: `evo-${agentId}-${Date.now()}`,
        project_id: 'system',
        title: `Evolution event for ${agentId}`,
        description: JSON.stringify(event),
        state: 'Done',
        tags: 'evolution,event',
      });
    } catch (error) {
      // Best effort
    }
  }

  async runCycle() {
    console.log('[Evolution] Starting evolution cycle...');

    try {
      const response = await axios.get(`${ASSET_BASE_URL}/api/agents`);
      const agents = response.data || [];

      for (const agent of agents) {
        if (agent.status === 'active') {
          await this.evolveAgent(agent.id);
        }
      }
    } catch (error) {
      console.error('[Evolution] Cycle error:', error.message);
    }

    console.log('[Evolution] Cycle complete');
  }

  async start() {
    this.running = true;
    console.log(`[Evolution] Engine started (interval: ${EVOLUTION_INTERVAL_MS}ms)`);

    while (this.running) {
      await this.runCycle();
      await new Promise(resolve => setTimeout(resolve, EVOLUTION_INTERVAL_MS));
    }
  }

  stop() {
    this.running = false;
  }
}

// CLI mode
if (require.main === module) {
  const engine = new EvolutionEngine();

  if (process.argv.includes('--once')) {
    engine.runCycle().then(() => process.exit(0));
  } else {
    engine.start();

    process.on('SIGINT', () => {
      engine.stop();
      process.exit(0);
    });
  }
}

module.exports = { EvolutionEngine };
