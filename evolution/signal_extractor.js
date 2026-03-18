/**
 * Signal extraction from ManageSim agent logs.
 *
 * Signals are typed observations extracted from agent activity:
 * - error: Task failures, exceptions
 * - drift: Agent behavior diverging from goals
 * - improvement: Identified optimization opportunities
 * - stagnation: No progress for extended period
 * - success: Consistent successful task completion
 */

function extractSignals(agentData) {
  const signals = [];
  const tasks = agentData.recentTasks || [];

  // Error signals — high failure rate
  const failedTasks = tasks.filter(t => t.success === false || t.success === 0);
  if (failedTasks.length > tasks.length * 0.3 && tasks.length >= 3) {
    signals.push({
      type: 'error',
      severity: 'high',
      message: `High failure rate: ${failedTasks.length}/${tasks.length} tasks failed`,
      data: { failure_rate: failedTasks.length / tasks.length },
    });
  }

  // Success signals — consistent success
  const successTasks = tasks.filter(t => t.success === true || t.success === 1);
  if (successTasks.length > tasks.length * 0.8 && tasks.length >= 5) {
    signals.push({
      type: 'success',
      severity: 'low',
      message: `Consistent success: ${successTasks.length}/${tasks.length} tasks succeeded`,
      data: { success_rate: successTasks.length / tasks.length },
    });
  }

  // Drift signals — tasks taking too long
  const avgDuration = tasks
    .filter(t => t.duration_seconds)
    .reduce((sum, t) => sum + t.duration_seconds, 0) / Math.max(tasks.filter(t => t.duration_seconds).length, 1);

  const slowTasks = tasks.filter(t => t.duration_seconds && t.duration_seconds > avgDuration * 2);
  if (slowTasks.length >= 2) {
    signals.push({
      type: 'drift',
      severity: 'medium',
      message: `${slowTasks.length} tasks took >2x average duration`,
      data: { avg_duration: avgDuration, slow_count: slowTasks.length },
    });
  }

  // Improvement signals — high cost tasks
  const highCostTasks = tasks.filter(t => t.cost > 0.01);
  if (highCostTasks.length >= 2) {
    signals.push({
      type: 'improvement',
      severity: 'medium',
      message: `${highCostTasks.length} high-cost tasks detected`,
      data: { high_cost_count: highCostTasks.length },
    });
  }

  // Stagnation signals — no recent tasks
  if (tasks.length === 0) {
    signals.push({
      type: 'stagnation',
      severity: 'high',
      message: 'No recent tasks found',
      data: {},
    });
  }

  // Error-learning signals — agent has error reports
  const errorReports = agentData.errorReports || [];
  const openErrors = errorReports.filter(r => r.status === 'open' || r.status === 'analyzing');
  const resolvedErrors = errorReports.filter(r => r.status === 'resolved');

  if (openErrors.length > 0) {
    signals.push({
      type: 'error',
      severity: openErrors.some(r => r.severity === 'critical' || r.severity === 'high') ? 'high' : 'medium',
      message: `${openErrors.length} unresolved error report(s) against this agent`,
      data: { open_errors: openErrors.length, error_types: [...new Set(openErrors.map(r => r.error_type))] },
    });
  }

  if (resolvedErrors.length > 0) {
    signals.push({
      type: 'improvement',
      severity: 'low',
      message: `${resolvedErrors.length} error(s) resolved with lessons learned`,
      data: { resolved_errors: resolvedErrors.length },
    });
  }

  return signals;
}

module.exports = { extractSignals };
