import { useRef, useState } from "react";
import { uploadDocument } from "../api/client";

export default function DocumentUpload({ onUploaded }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);

  async function handleFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }
    setError("");
    setUploading(true);
    try {
      await uploadDocument(file);
      onUploaded?.();
      if (inputRef.current) inputRef.current.value = "";
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="card upload-card">
      <h2>Upload PDF</h2>
      <p className="muted">
        Text, tables, and images are extracted and indexed in your private workspace.
      </p>
      <div
        className={`dropzone ${dragOver ? "drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFile(e.dataTransfer.files[0]);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={(e) => handleFile(e.target.files[0])}
          disabled={uploading}
        />
        <div className="dropzone-inner">
          <span className="drop-icon">📄</span>
          <p>{uploading ? "Uploading & queuing…" : "Drop a PDF here or click to browse"}</p>
        </div>
      </div>
      {error && <p className="error-text">{error}</p>}
    </section>
  );
}
