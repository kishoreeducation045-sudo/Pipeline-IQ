import { useEffect, useState } from "react";
import Feed from "./pages/Feed";
import FailureDetail from "./pages/FailureDetail";
import Metrics from "./pages/Metrics";

export default function App() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const handler = () => setPath(window.location.pathname);
    window.addEventListener("popstate", handler);

    // Intercept all in-app anchor clicks for SPA routing
    const clickHandler = (e: MouseEvent) => {
      const t = e.target as HTMLElement;
      const a = t.closest("a");
      if (!a) return;
      const href = a.getAttribute("href");
      if (!href || !href.startsWith("/")) return;
      if (a.getAttribute("target") === "_blank") return;
      e.preventDefault();
      history.pushState({}, "", href);
      setPath(href);
    };
    document.addEventListener("click", clickHandler);

    return () => {
      window.removeEventListener("popstate", handler);
      document.removeEventListener("click", clickHandler);
    };
  }, []);

  const detailMatch = path.match(/^\/failure\/(.+)$/);

  return (
    <div>
      <nav className="border-b bg-white px-8 py-3 flex gap-6 items-center">
        <a href="/" className="font-bold text-lg">PipelineIQ</a>
        <a href="/" className="text-sm hover:text-blue-600">Feed</a>
        <a href="/metrics" className="text-sm hover:text-blue-600">Metrics</a>
        <span className="ml-auto text-xs text-neutral-500">
          AI-powered RCA · Claude Sonnet 4.5
        </span>
      </nav>
      {path === "/" && <Feed />}
      {path === "/metrics" && <Metrics />}
      {detailMatch && <FailureDetail id={detailMatch[1]} />}
    </div>
  );
}
