import { useState } from "react";
import { queryDocuments } from "../api/client";

function formatCost(usd) {
  if (!usd || usd === 0) return "$0.00";
  if (usd < 0.01) return `$${usd.toFixed(6)}`;
  return `$${usd.toFixed(4)}`;
}

export default function ChatPanel({ selectedIds, hasReadyDocs, conversationId, onNewConversation }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState([]);

  async function handleSubmit(e) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;

    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setQuery("");
    setLoading(true);
    setError("");

    try {
      const data = await queryDocuments({
        query: q,
        documentIds: selectedIds,
        conversationId,
      });

      if (data.conversation_id && !conversationId) {
        onNewConversation?.(data.conversation_id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          cost: data.cost,
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card chat-card">
      <h2>Ask your documents</h2>
      <p className="muted">
        Questions are answered from retrieved text, tables, and image descriptions.
      </p>

      {!hasReadyDocs && (
        <div className="banner banner-warn">
          Upload a PDF and wait until status is <strong>Ready</strong> before querying.
        </div>
      )}

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble chat-${msg.role}`}>
            <div className="bubble-label">{msg.role === "user" ? "You" : "Assistant"}</div>
            <p className="bubble-text">{msg.content}</p>

            {msg.cost && (
              <div className="cost-badge">
                <span>{msg.cost.total_tokens} tokens</span>
                <span>{formatCost(msg.cost.estimated_cost_usd)}</span>
                <span>{msg.cost.latency_ms}ms</span>
              </div>
            )}

            {msg.sources?.length > 0 && (
              <div className="sources-inline">
                <div className="sources-toggle-label">Sources ({msg.sources.length})</div>
                <ul>
                  {msg.sources.map((src, j) => (
                    <li key={j}>
                      <div className="source-head">
                        <span className={`chip chip-${src.chunk_type}`}>{src.chunk_type}</span>
                        {src.page != null && <span>Page {src.page}</span>}
                        {src.document_name && <span>{src.document_name}</span>}
                        {src.score != null && <span>score {src.score}</span>}
                      </div>
                      <p>{src.content}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-bubble chat-assistant">
            <div className="bubble-label">Assistant</div>
            <p className="bubble-text typing">Thinking...</p>
          </div>
        )}
      </div>

      {error && <p className="error-text">{error}</p>}

      <form onSubmit={handleSubmit} className="chat-form">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. What are the main findings in the tables on page 2?"
          rows={2}
          disabled={loading}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !query.trim()}>
          {loading ? "Searching..." : "Send"}
        </button>
      </form>
    </section>
  );
}
