import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-icon">◈</span>
          <div>
            <h1>Multimodal RAG</h1>
            <p>PDF text · tables · images</p>
          </div>
        </div>
        {user && (
          <div className="topbar-actions">
            <nav className="nav-links">
              <Link to="/" className={location.pathname === "/" ? "active" : ""}>
                Dashboard
              </Link>
              <Link to="/usage" className={location.pathname === "/usage" ? "active" : ""}>
                Usage & Costs
              </Link>
            </nav>
            <span className="user-pill">@{user.username}</span>
            <button type="button" className="btn btn-ghost" onClick={logout}>
              Log out
            </button>
          </div>
        )}
      </header>
      <main className="main-content">{children}</main>
      <footer className="footer">
        <span>FastAPI · LangChain · ChromaDB · OpenAI</span>
        <span>v1.0.0</span>
      </footer>
    </div>
  );
}
