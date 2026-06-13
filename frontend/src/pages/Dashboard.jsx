import { useCallback, useEffect, useState } from "react";
import ChatPanel from "../components/ChatPanel";
import DocumentList from "../components/DocumentList";
import DocumentUpload from "../components/DocumentUpload";
import Layout from "../components/Layout";
import {
  deleteConversation,
  fetchConversations,
  fetchDocuments,
  fetchHealth,
} from "../api/client";

export default function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [health, setHealth] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);

  const loadDocuments = useCallback(async () => {
    try {
      const data = await fetchDocuments();
      setDocuments(data);
      setLoadError("");
      setSelectedIds((prev) =>
        prev.filter((id) => data.some((d) => d.id === id && d.status === "ready"))
      );
    } catch (err) {
      setLoadError(err.message);
    }
  }, []);

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await fetchConversations());
    } catch {}
  }, []);

  useEffect(() => {
    loadDocuments();
    loadConversations();
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth({ openai_configured: false }));
  }, [loadDocuments, loadConversations]);

  useEffect(() => {
    const hasProcessing = documents.some(
      (d) => d.status === "pending" || d.status === "processing"
    );
    if (!hasProcessing) return;
    const timer = setInterval(loadDocuments, 4000);
    return () => clearInterval(timer);
  }, [documents, loadDocuments]);

  function toggleSelect(id) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function handleDeleteConversation(id) {
    if (!confirm("Delete this conversation?")) return;
    try {
      await deleteConversation(id);
      if (activeConvId === id) setActiveConvId(null);
      loadConversations();
    } catch {}
  }

  const hasReadyDocs = documents.some((d) => d.status === "ready");

  return (
    <Layout>
      {health && !health.openai_configured && (
        <div className="banner banner-warn">
          <strong>OpenAI API key not configured.</strong> Set <code>OPENAI_API_KEY</code> in your
          backend <code>.env</code> file to enable embeddings and chat.
        </div>
      )}

      {loadError && <p className="error-text">{loadError}</p>}

      <div className="dashboard-grid">
        <div className="dashboard-side">
          <DocumentUpload onUploaded={loadDocuments} />
          <DocumentList
            documents={documents}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onRefresh={loadDocuments}
            onDeleted={(id) => {
              setSelectedIds((prev) => prev.filter((x) => x !== id));
              loadDocuments();
            }}
          />

          {conversations.length > 0 && (
            <section className="card">
              <h2>Conversations</h2>
              <ul className="conv-list">
                {conversations.map((c) => (
                  <li
                    key={c.id}
                    className={`conv-item ${activeConvId === c.id ? "active" : ""}`}
                  >
                    <button
                      className="conv-btn"
                      onClick={() => setActiveConvId(c.id === activeConvId ? null : c.id)}
                    >
                      <strong>{c.title}</strong>
                      <span className="doc-meta">
                        {c.message_count} messages
                      </span>
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDeleteConversation(c.id)}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <ChatPanel
          selectedIds={selectedIds}
          hasReadyDocs={hasReadyDocs}
          conversationId={activeConvId}
          onNewConversation={(id) => {
            setActiveConvId(id);
            loadConversations();
          }}
        />
      </div>
    </Layout>
  );
}
