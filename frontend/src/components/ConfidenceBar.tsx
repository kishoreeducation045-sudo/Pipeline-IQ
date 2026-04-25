import React from "react";

interface ConfidenceBarProps {
  value: number;
  label?: string;
}

export const ConfidenceBar: React.FC<ConfidenceBarProps> = ({ value, label = "Confidence" }) => {
  // value is expected to be 0 to 1
  const percentage = Math.min(Math.max((value * 100).toFixed(0), 0), 100);
  
  let color = "bg-rose-500";
  if (value > 0.8) color = "bg-emerald-500";
  else if (value > 0.6) color = "bg-blue-500";
  else if (value > 0.4) color = "bg-amber-500";

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400">{label}</span>
        <span className="text-slate-300 font-mono">{percentage}%</span>
      </div>
      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} transition-all duration-700 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};
