"use client";

import React, { useState } from "react";
import {
  History,
  X,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Clock,
  Code,
  ChevronRight,
  Database,
  RefreshCw,
} from "lucide-react";
import { soundSynth } from "@/utils/audioSynthesizer";

interface PipelineRun {
  id: string;
  session_id: string;
  status: "running" | "done" | "failed";
  stages: any[];
  created_at: string;
  completed_at?: string;
  total_latency_ms: number;
}

interface TelemetrySidebarProps {
  isOpen: boolean;
  onClose: () => void;
  history: PipelineRun[];
  onSelectRun: (run: PipelineRun) => void;
  onFetchHistory: () => void;
}

export const TelemetrySidebar: React.FC<TelemetrySidebarProps> = ({
  isOpen,
  onClose,
  history,
  onSelectRun,
  onFetchHistory,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "done" | "failed">("all");

  if (!isOpen) return null;

  const filteredHistory = history.filter((run) => {
    const matchesSearch = run.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || run.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <aside className="fixed top-0 right-0 bottom-0 z-40 w-full sm:w-96 bg-[#030712]/95 backdrop-blur-2xl border-l border-slate-800 shadow-2xl flex flex-col font-mono select-none">
      {/* Drawer Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-widest font-hud">
            TELEMETRY RUN LOGS
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              soundSynth.playClick();
              onFetchHistory();
            }}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-400"
            title="Refresh logs"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              soundSynth.playClick();
              onClose();
            }}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-3 border-b border-slate-800/80 space-y-2">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search Run ID..."
            className="w-full pl-9 pr-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-500">STATUS:</span>
          <button
            onClick={() => setStatusFilter("all")}
            className={`px-2 py-0.5 rounded text-[10px] ${
              statusFilter === "all"
                ? "bg-cyan-950 text-cyan-300 border border-cyan-500/40"
                : "text-slate-400 hover:text-white"
            }`}
          >
            ALL
          </button>
          <button
            onClick={() => setStatusFilter("done")}
            className={`px-2 py-0.5 rounded text-[10px] ${
              statusFilter === "done"
                ? "bg-emerald-950 text-emerald-300 border border-emerald-500/40"
                : "text-slate-400 hover:text-white"
            }`}
          >
            DONE
          </button>
          <button
            onClick={() => setStatusFilter("failed")}
            className={`px-2 py-0.5 rounded text-[10px] ${
              statusFilter === "failed"
                ? "bg-rose-950 text-rose-300 border border-rose-500/40"
                : "text-slate-400 hover:text-white"
            }`}
          >
            FAILED
          </button>
        </div>
      </div>

      {/* Run List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filteredHistory.length === 0 ? (
          <div className="text-center py-10 text-slate-500 text-xs">
            No pipeline runs logged in Supabase.
          </div>
        ) : (
          filteredHistory.map((run) => (
            <div
              key={run.id}
              onClick={() => {
                soundSynth.playClick();
                onSelectRun(run);
              }}
              className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 cursor-pointer transition-all duration-200"
            >
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-bold text-white truncate max-w-[150px]">
                  {run.id.substring(0, 12)}...
                </span>
                {run.status === "done" ? (
                  <span className="text-[10px] font-bold text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> DONE
                  </span>
                ) : (
                  <span className="text-[10px] font-bold text-rose-400 flex items-center gap-1">
                    <XCircle className="w-3 h-3" /> FAILED
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between text-[10px] text-slate-400 mt-2">
                <span>{new Date(run.created_at).toLocaleTimeString()}</span>
                <span className="text-cyan-400 font-bold">{run.total_latency_ms} ms</span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-slate-800 text-[10px] text-slate-500 text-center">
        SUPABASE PERSISTENCE ENGINE // REAL-TIME RUN LOGS
      </div>
    </aside>
  );
};
