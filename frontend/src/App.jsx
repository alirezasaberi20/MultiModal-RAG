import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import UsageDashboard from "./pages/UsageDashboard";
import { useAuth } from "./context/AuthContext";

function PublicOnly({ children }) {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/usage" element={<UsageDashboard />} />
      </Route>
      <Route
        path="/login"
        element={<PublicOnly><Login /></PublicOnly>}
      />
      <Route
        path="/register"
        element={<PublicOnly><Register /></PublicOnly>}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
