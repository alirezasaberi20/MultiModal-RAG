import { deleteDocument } from "../api/client";

const STATUS_LABELS = {
  pending: "Queued",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatMs(ms) {
  if (!ms) return "";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function DocumentList({
  documents,
  selectedIds,
  onToggleSelect,
  onRefresh,
  onDeleted,
}) {
  async function handleDelete(id) {
    if (!confirm("Delete this document and its vectors?")) return;
    try {
      await deleteDocument(id);
      onDeleted?.(id);
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <section className="card">
      <div className="card-header">
        <h2>Your documents</h2>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onRefresh}>
          Refresh
        </button>
      </div>

      {documents.length === 0 ? (
        <p className="muted empty-state">No documents yet. Upload a PDF to get started.</p>
      ) : (
        <ul className="doc-list">
          {documents.map((doc) => (
            <li key={doc.id} className={`doc-item status-${doc.status}`}>
              <label className="doc-select">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(doc.id)}
                  disabled={doc.status !== "ready"}
                  onChange={() => onToggleSelect(doc.id)}
                />
                <div>
                  <strong>{doc.original_name}</strong>
                  <span className="doc-meta">
                    {STATUS_LABELS[doc.status] || doc.status}
                    {doc.chunk_count > 0 && ` · ${doc.chunk_count} chunks`}
                    {doc.file_size_bytes > 0 && ` · ${formatBytes(doc.file_size_bytes)}`}
                    {doc.processing_time_ms > 0 && ` · ${formatMs(doc.processing_time_ms)}`}
                  </span>
                  {doc.error_message && (
                    <span className="error-text small">{doc.error_message}</span>
                  )}
                </div>
              </label>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => handleDelete(doc.id)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="muted small">
        Select documents to query, or leave none selected to search all ready files.
      </p>
    </section>
  );
}
