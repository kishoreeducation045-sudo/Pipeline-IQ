import React from "react";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = "md" }) => {
  const norm = status.toLowerCase();
  
  let label = `• ${status}`;
  let colorClass = "bg-slate-900/50 text-slate-400 border-slate-800";
  
  if (norm === "failure") {
    label = "✗ failure";
    colorClass = "bg-rose-900/50 text-rose-500 border-rose-800/50";
  } else if (norm === "cancelled" || norm === "timed_out") {
    label = `! ${norm}`;
    colorClass = "bg-amber-900/50 text-amber-500 border-amber-800/50";
  } else if (norm === "success" || norm === "ok") {
    label = "✓ success";
    colorClass = "bg-emerald-900/50 text-emerald-500 border-emerald-800/50";
  } else if (norm === "flaky") {
    label = "⚡ flaky";
    colorClass = "bg-violet-900/50 text-violet-400 border-violet-800/50";
  }

  const px = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-3 py-1 text-xs";
  
  return (
    <span className={`inline-flex items-center rounded-full font-medium border ${px} ${colorClass}`}>
      {label}
    </span>
  );
};
