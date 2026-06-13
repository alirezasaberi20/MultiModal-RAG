import { useCallback, useEffect, useState } from "react";
import Layout from "../components/Layout";
import { fetchUsageAnalytics } from "../api/client";

function formatCost(usd) {
  if (!usd || usd === 0) return "$0.00";
  if (usd < 0.01) return `$${usd.toFixed(6)}`;
  return `$${usd.toFixed(4)}`;
}

function StatCard({ label, value, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

export default function UsageDashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [days, setDays] = useState(30);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await fetchUsageAnalytics(days);
      setAnalytics(data);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  const summary = analytics?.summary;
  const daily = analytics?.daily_usage || [];
  const costByOp = analytics?.cost_by_operation || {};
  const maxTokens = Math.max(...daily.map((d) => d.tokens), 1);

  return (
    <Layout>
      <div className="usage-page">
        <div className="usage-header">
          <h2>Usage & Cost Analytics</h2>
          <div className="period-select">
            {[7, 30, 90].map((d) => (
              <button
                key={d}
                className={`btn btn-sm ${days === d ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setDays(d)}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        {error && <p className="error-text">{error}</p>}

        {summary && (
          <>
            <div className="stats-grid">
              <StatCard label="Total Queries" value={summary.total_queries} />
              <StatCard label="Documents" value={summary.total_documents} />
              <StatCard label="Total Tokens" value={summary.total_tokens_used.toLocaleString()} />
              <StatCard label="Total Cost" value={formatCost(summary.total_cost_usd)} />
              <StatCard
                label="Avg. Cost / Query"
                value={formatCost(summary.avg_cost_per_query_usd)}
              />
              <StatCard
                label="Avg. Latency"
                value={`${Math.round(summary.avg_latency_ms)}ms`}
              />
            </div>

            {Object.keys(costByOp).length > 0 && (
              <div className="card cost-breakdown">
                <h3>Cost by Operation</h3>
                <div className="op-bars">
                  {Object.entries(costByOp)
                    .sort(([, a], [, b]) => b - a)
                    .map(([op, cost]) => {
                      const totalCost = Object.values(costByOp).reduce((a, b) => a + b, 0);
                      const pct = totalCost > 0 ? (cost / totalCost) * 100 : 0;
                      return (
                        <div key={op} className="op-bar-row">
                          <span className="op-name">{op}</span>
                          <div className="op-bar-track">
                            <div className="op-bar-fill" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="op-cost">{formatCost(cost)}</span>
                        </div>
                      );
                    })}
                </div>
              </div>
            )}

            {daily.length > 0 && (
              <div className="card daily-chart">
                <h3>Daily Token Usage</h3>
                <div className="bar-chart">
                  {daily.map((d) => (
                    <div key={d.date} className="bar-col">
                      <div
                        className="bar-fill"
                        style={{ height: `${(d.tokens / maxTokens) * 100}%` }}
                        title={`${d.date}: ${d.tokens.toLocaleString()} tokens, ${d.queries} queries, ${formatCost(d.cost_usd)}`}
                      />
                      <span className="bar-label">
                        {d.date.slice(5)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
