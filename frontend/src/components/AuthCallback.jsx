import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { exchangeSession } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

// Processes #session_id=... returned by Emergent Auth.
// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export const AuthCallback = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    const sessionId = match ? match[1] : null;

    if (!sessionId) {
      navigate("/", { replace: true });
      return;
    }

    exchangeSession(sessionId)
      .then((res) => {
        setUser(res.data);
        toast.success(`Welcome, ${res.data.name}`);
        navigate("/", { replace: true, state: { user: res.data } });
      })
      .catch(() => {
        toast.error("Sign-in failed. Please try again.");
        navigate("/auth", { replace: true });
      });
  }, [location.hash, navigate, setUser]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background" data-testid="auth-callback-loading">
      <div className="flex items-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
        <span className="font-heading text-lg">Signing you in…</span>
      </div>
    </div>
  );
};
