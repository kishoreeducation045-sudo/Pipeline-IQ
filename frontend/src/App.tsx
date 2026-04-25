import React, { useEffect, useState } from "react";

function usePath() {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);

    // monkey patch pushState
    const originalPushState = window.history.pushState;
    window.history.pushState = function (...args) {
      originalPushState.apply(this, args);
      setPath(window.location.pathname);
    };

    return () => {
      window.removeEventListener("popstate", onPopState);
      window.history.pushState = originalPushState;
    };
  }, []);
  return path;
}

export function navigate(to: string) {
  window.history.pushState({}, "", to);
}

// Lazy load pages to avoid circular imports during setup
import { Feed } from "./pages/Feed";
import { Metrics } from "./pages/Metrics";
import { FailureDetail } from "./pages/FailureDetail";

export default function App() {
  const path = usePath();
  const [backendUp, setBackendUp] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const base = (import.meta.env.VITE_API_BASE as string) ?? "http://localhost:8000";
        const r = await fetch(`${base}/health`);
        setBackendUp(r.ok);
      } catch {
        setBackendUp(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-300 font-sans overflow-hidden">
      {/* SIDEBAR */}
      <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col justify-between shrink-0 hidden md:flex">
        <div>
          <div className="p-6">
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <span className="text-indigo-500">⚡</span> PipelineIQ
            </h1>
            <p className="text-slate-500 text-xs mt-1">AI-powered RCA</p>
          </div>
          
          <nav className="px-4 space-y-1">
            <button 
              onClick={() => navigate("/")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200
                ${path === "/" ? "bg-indigo-600/10 text-indigo-400" : "text-slate-400 hover:bg-slate-900 hover:text-white"}`}
            >
              <span>⊞</span> Feed
            </button>
            <button 
              onClick={() => navigate("/metrics")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200
                ${path === "/metrics" ? "bg-indigo-600/10 text-indigo-400" : "text-slate-400 hover:bg-slate-900 hover:text-white"}`}
            >
              <span>📊</span> Metrics / ROI
            </button>
          </nav>
        </div>

        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-2 mb-2 text-xs">
            <span className={`h-2 w-2 rounded-full ${backendUp ? "bg-emerald-500" : "bg-rose-500"}`}></span>
            <span className={backendUp ? "text-emerald-400" : "text-rose-400"}>
              Backend {backendUp ? "Online" : "Offline"}
            </span>
          </div>
          <p className="text-slate-500 text-[10px]">v0.1.0 · Gemini</p>
        </div>
      </aside>

      {/* MOBILE TOPBAR */}
      <div className="md:hidden fixed top-0 w-full h-14 bg-slate-950 border-b border-slate-800 flex items-center px-4 z-50 justify-between">
        <h1 className="text-lg font-bold text-white flex items-center gap-2">
          <span className="text-indigo-500">⚡</span> PipelineIQ
        </h1>
        <div className="flex gap-4">
          <button onClick={() => navigate("/")} className={path === "/" ? "text-indigo-400" : "text-slate-400"}>Feed</button>
          <button onClick={() => navigate("/metrics")} className={path === "/metrics" ? "text-indigo-400" : "text-slate-400"}>Metrics</button>
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 overflow-y-auto w-full md:mt-0 mt-14">
        <div className="max-w-6xl mx-auto w-full">
          {path === "/" && <Feed />}
          {path === "/metrics" && <Metrics />}
          {path.startsWith("/failure/") && <FailureDetail id={path.split("/")[2]} />}
        </div>
      </main>
    </div>
  );
}
