import React from "react";

export const LiveIndicator: React.FC = () => {
  return (
    <div className="flex items-center gap-2 px-2 py-1 bg-slate-900/50 border border-slate-800 rounded-full">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
      </span>
      <span className="text-[10px] font-bold tracking-widest uppercase text-emerald-500 mx-1">Live</span>
    </div>
  );
};
