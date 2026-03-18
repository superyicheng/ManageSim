/**
 * Capsule sharing — proven solutions shared across agents.
 *
 * A Capsule is a record of a successful solution:
 * - Gene that was mutated
 * - What changed
 * - Performance improvement measured
 * - Visibility scope (team/project/public)
 */

const axios = require('axios');

const ASSET_BASE_URL = process.env.ASSET_BASE_URL || 'http://localhost:8100';

class Capsule {
  constructor(data = {}) {
    this.id = data.id || `capsule-${Date.now()}`;
    this.agent_id = data.agent_id || '';
    this.gene_id = data.gene_id || '';
    this.description = data.description || '';
    this.improvement = data.improvement || 0;
    this.changes = data.changes || {};
    this.visibility = data.visibility || 'team';
    this.created_at = data.created_at || new Date().toISOString();
    this.adopted_by = data.adopted_by || [];
  }

  toJSON() {
    return {
      id: this.id,
      agent_id: this.agent_id,
      gene_id: this.gene_id,
      description: this.description,
      improvement: this.improvement,
      changes: this.changes,
      visibility: this.visibility,
      created_at: this.created_at,
      adopted_by: this.adopted_by,
    };
  }
}

async function shareCapsule(capsule) {
  try {
    await axios.post(`${ASSET_BASE_URL}/api/skills`, {
      id: capsule.id,
      name: `Capsule: ${capsule.description}`,
      description: JSON.stringify(capsule.toJSON()),
      level: capsule.visibility === 'public' ? 'server' : 'team',
      level_id: capsule.agent_id,
      source: 'evolution',
      tags: `capsule,evolution,${capsule.gene_id}`,
    });
    return true;
  } catch (error) {
    console.warn(`Failed to share capsule: ${error.message}`);
    return false;
  }
}

async function findCapsules(geneId, visibility = 'public') {
  try {
    const response = await axios.get(`${ASSET_BASE_URL}/api/skills`, {
      params: { level: visibility === 'public' ? 'server' : 'team' },
    });
    return (response.data || []).filter(s =>
      s.tags && s.tags.includes('capsule') && s.tags.includes(geneId)
    );
  } catch (error) {
    return [];
  }
}

async function adoptCapsule(capsuleId, agentId) {
  console.log(`Agent ${agentId} adopting capsule ${capsuleId}`);
  // Adoption logic: apply the capsule's changes to the adopting agent
  // This would be implemented via the evolution engine
  return true;
}

module.exports = { Capsule, shareCapsule, findCapsules, adoptCapsule };
