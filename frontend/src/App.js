import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { AuthCallback } from "@/components/AuthCallback";
import HomePage from "@/pages/HomePage";
import AuthPage from "@/pages/AuthPage";
import RedirectPage from "@/pages/RedirectPage";

function AppRouter() {
  const location = useLocation();
  // Synchronous check during render: process OAuth session_id BEFORE any route runs.
  // Read from useLocation().hash (reactive), not window.location.hash.
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/:code" element={<RedirectPage />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <AppRouter />
          <Toaster position="bottom-right" />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
