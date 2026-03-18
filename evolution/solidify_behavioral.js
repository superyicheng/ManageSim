/**
 * Behavioral solidification — updates agent soul.md/CLAUDE.md
 * instead of modifying code files (Evolver's default).
 */

const axios = require('axios');
const { PersonalityState } = require('./personality');

const ASSET_BASE_URL = process.env.ASSET_BASE_URL || 'http://localhost:8100';

async function solidifyBehavioral(agentData, mutation) {
  const changes = mutation.changes;
  const result = { updated: [] };

  // Update personality state
  if (changes.personality_adjustments && Object.keys(changes.personality_adjustments).length > 0) {
    let currentState;
    try {
      currentState = new PersonalityState(
        JSON.parse(agentData.personality_state || '{}')
      );
    } catch {
      currentState = PersonalityState.forRole(agentData.role);
    }

    currentState.apply(changes.personality_adjustments);

    try {
      await axios.patch(`${ASSET_BASE_URL}/api/agents/${agentData.id}`, {
        personality_state: JSON.stringify(currentState.toJSON()),
      });
      result.updated.push('personality_state');
    } catch (error) {
      console.warn(`Failed to update personality for ${agentData.id}`);
    }
  }

  // Record soul.md additions (to be applied when agent context is loaded)
  if (changes.soul_additions && changes.soul_additions.length > 0) {
    // Store as evolution chunk in Easybase
    try {
      await axios.post(`${ASSET_BASE_URL}/api/tasks`, {
        id: `soul-update-${agentData.id}-${Date.now()}`,
        project_id: agentData.project_id,
        title: `Soul.md evolution for ${agentData.name}`,
        description: changes.soul_additions.join('\n'),
        state: 'Done',
        tags: 'evolution,soul-update',
      });
      result.updated.push('soul_additions');
    } catch (error) {
      console.warn(`Failed to store soul additions for ${agentData.id}`);
    }
  }

  // Record CLAUDE.md additions
  if (changes.claude_additions && changes.claude_additions.length > 0) {
    try {
      await axios.post(`${ASSET_BASE_URL}/api/tasks`, {
        id: `claude-update-${agentData.id}-${Date.now()}`,
        project_id: agentData.project_id,
        title: `CLAUDE.md evolution for ${agentData.name}`,
        description: changes.claude_additions.join('\n'),
        state: 'Done',
        tags: 'evolution,claude-update',
      });
      result.updated.push('claude_additions');
    } catch (error) {
      console.warn(`Failed to store claude additions for ${agentData.id}`);
    }
  }

  return result;
}

module.exports = { solidifyBehavioral };
