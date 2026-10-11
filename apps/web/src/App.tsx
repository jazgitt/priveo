import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { NAV } from "./nav";
import { Placeholder } from "./pages/Placeholder";
import { SignIn } from "./pages/SignIn";
import { Shell } from "./Shell";

function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <p className="loading">Loading...</p>;
  if (status === "signedOut") {
    return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignIn />} />
      <Route element={<RequireAuth />}>
        <Route element={<Shell />}>
          {NAV.map((item) => (
            <Route key={item.path} path={item.path} element={<Placeholder item={item} />} />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
