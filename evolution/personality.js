/**
 * PersonalityState — 5 evolving dimensions per agent.
 *
 * Dimensions:
 *   rigor (0-1):          Protocol adherence
 *   creativity (0-1):     Improvisation vs pattern reuse
 *   verbosity (0-1):      Explanation detail
 *   risk_tolerance (0-1): Change magnitude acceptance
 *   obedience (0-1):      Directive compliance
 */

class PersonalityState {
  constructor(state = {}) {
    this.rigor = state.rigor ?? 0.75;
    this.creativity = state.creativity ?? 0.35;
    this.verbosity = state.verbosity ?? 0.25;
    this.risk_tolerance = state.risk_tolerance ?? 0.40;
    this.obedience = state.obedience ?? 0.85;
  }

  static forRole(role) {
    const archetypes = {
      leader: new PersonalityState({
        rigor: 0.80, creativity: 0.50, verbosity: 0.40,
        risk_tolerance: 0.45, obedience: 0.70,
      }),
      worker: new PersonalityState({
        rigor: 0.90, creativity: 0.20, verbosity: 0.20,
        risk_tolerance: 0.25, obedience: 0.90,
      }),
      reviewer: new PersonalityState({
        rigor: 0.90, creativity: 0.30, verbosity: 0.50,
        risk_tolerance: 0.20, obedience: 0.85,
      }),
      researcher: new PersonalityState({
        rigor: 0.75, creativity: 0.60, verbosity: 0.50,
        risk_tolerance: 0.50, obedience: 0.65,
      }),
    };
    return archetypes[role] || new PersonalityState();
  }

  apply(adjustments) {
    for (const [dim, delta] of Object.entries(adjustments)) {
      if (this[dim] !== undefined && typeof delta === 'number') {
        this[dim] = Math.max(0, Math.min(1, this[dim] + delta));
      }
    }
    return this;
  }

  toJSON() {
    return {
      rigor: Math.round(this.rigor * 100) / 100,
      creativity: Math.round(this.creativity * 100) / 100,
      verbosity: Math.round(this.verbosity * 100) / 100,
      risk_tolerance: Math.round(this.risk_tolerance * 100) / 100,
      obedience: Math.round(this.obedience * 100) / 100,
    };
  }

  toString() {
    return JSON.stringify(this.toJSON(), null, 2);
  }
}

module.exports = { PersonalityState };
