"use client";

import React, { useState, useEffect } from "react";
import {
  Terminal,
  Activity,
  Volume2,
  VolumeX,
  Settings,
  History,
  Cpu,
  Radio,
  Wifi,
  WifiOff,
  Sparkles,
} from "lucide-react";
import { soundSynth } from "@/utils/audioSynthesizer";

interface HudHeaderProps {
  status: "idle" | "recording" | "processing" | "playing" | "error";
  backendUrl: string;
  sessionId: string;
  onOpenSettings: () => void;
  onToggleSidebar: () => void;
  isSidebarOpen: boolean;
  soundEnabled: boolean;
  onToggleSound: () => void;
}

export const HudHeader: React.FC<HudHeaderProps> = ({
  status,
  backendUrl,
  sessionId,
  onOpenSettings,
  onToggleSidebar,
  isSidebarOpen,
  soundEnabled,
  onToggleSound,
}) => {
  const [timeString, setTimeString] = useState("");
  const [dateString, setDateString] = useState("");
  const [pingMs, setPingMs] = useState<number | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState(true);

  // Digital Clock Updater
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeString(
        now.toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
      setDateString(
        now.toLocaleDateString("en-US", {
          year: "numeric",
          month: "short",
          day: "2-digit",
        })
      );
    };

    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Health Ping Checker
  useEffect(() => {
    const checkHealth = async () => {
      const start = performance.now();
      try {
        const res = await fetch(`${backendUrl}/health`, { signal: AbortSignal.timeout(3000) });
        if (res.ok) {
          const latency = Math.round(performance.now() - start);
          setPingMs(latency);
          setIsBackendHealthy(true);
        } else {
          setIsBackendHealthy(false);
          setPingMs(null);
        }
      } catch (err) {
        setIsBackendHealthy(false);
        setPingMs(null);
      }
    };

    checkHealth();
    const pingTimer = setInterval(checkHealth, 10000);
    return () => clearInterval(pingTimer);
  }, [backendUrl]);

  return (
    <header className="relative z-20 w-full px-3 sm:px-6 py-2.5 sm:py-3 border-b border-slate-800/80 bg-[#030712]/90 backdrop-blur-xl flex items-center justify-between gap-2 sm:gap-4 select-none">
      {/* Brand Title & System Badge */}
      <div className="flex items-center gap-2 sm:gap-3">
        <div className="relative flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-cyan-950/40 border border-cyan-500/40 glow-cyan shrink-0">
          <Cpu className="w-4 h-4 sm:w-5 sm:h-5 text-cyan-400 animate-pulse" />
          <div className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
        </div>

        <div>
          <div className="flex items-center gap-1.5 sm:gap-2">
            <h1 className="text-base sm:text-lg font-bold tracking-widest text-white uppercase font-hud">
              ULTRON <span className="text-cyan-400 text-glow-cyan">V1</span>
            </h1>
            <span className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
              HUD COCKPIT
            </span>
          </div>

          <p className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
            <Radio className="w-3 h-3 text-cyan-400 animate-pulse" />
            STATE:{" "}
            <span
              className={`font-semibold uppercase tracking-wider ${
                status === "recording"
                  ? "text-rose-400 text-glow-crimson"
                  : status === "processing"
                  ? "text-amber-400"
                  : status === "playing"
                  ? "text-emerald-400"
                  : status === "error"
                  ? "text-red-500"
                  : "text-cyan-400"
              }`}
            >
              {status}
            </span>
          </p>
        </div>
      </div>

      {/* Center Telemetry Metrics */}
      <div className="hidden lg:flex items-center gap-6 px-4 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 font-mono text-xs text-slate-300">
        <div className="flex items-center gap-2">
          {isBackendHealthy ? (
            <Wifi className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-rose-400" />
          )}
          <span className="text-slate-400">API:</span>
          <span className={isBackendHealthy ? "text-emerald-400 font-semibold" : "text-rose-400"}>
            {isBackendHealthy ? `ONLINE (${pingMs ?? "--"}ms)` : "OFFLINE"}
          </span>
        </div>

        <div className="h-3 w-px bg-slate-800" />

        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-slate-400">SESSION:</span>
          <span className="text-cyan-300 truncate max-w-[120px]" title={sessionId}>
            {sessionId.substring(0, 10)}...
          </span>
        </div>

        <div className="h-3 w-px bg-slate-800" />

        <div className="flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-slate-400">STT/LLM:</span>
          <span className="text-slate-200">GROQ // LLAMA3</span>
        </div>
      </div>

      {/* Right Controls & Digital Clock */}
      <div className="flex items-center gap-3">
        {/* System Time */}
        <div className="hidden md:flex flex-col text-right font-mono text-xs">
          <span className="text-cyan-400 font-bold tracking-widest">{timeString || "00:00:00"}</span>
          <span className="text-[10px] text-slate-400 uppercase">{dateString || "2026"}</span>
        </div>

        <div className="h-6 w-px bg-slate-800 hidden md:block" />

        {/* Sound FX Toggle */}
        <button
          onClick={() => {
            soundSynth.playClick();
            onToggleSound();
          }}
          className={`p-2 rounded-lg border transition-all duration-200 ${
            soundEnabled
              ? "bg-cyan-950/40 border-cyan-500/40 text-cyan-400 hover:bg-cyan-900/50"
              : "bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300"
          }`}
          title={soundEnabled ? "Mute UI Sound FX" : "Enable UI Sound FX"}
          aria-label="Toggle Sound"
        >
          {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
        </button>

        {/* History Drawer Button */}
        <button
          onClick={() => {
            soundSynth.playClick();
            onToggleSidebar();
          }}
          className={`px-3 py-2 rounded-lg border text-xs font-mono flex items-center gap-1.5 transition-all duration-200 ${
            isSidebarOpen
              ? "bg-cyan-950/50 border-cyan-500/50 text-cyan-300 glow-cyan"
              : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
          }`}
        >
          <History className="w-4 h-4 text-cyan-400" />
          <span className="hidden sm:inline">TELEMETRY LOGS</span>
        </button>

        {/* Settings Launcher */}
        <button
          onClick={() => {
            soundSynth.playClick();
            onOpenSettings();
          }}
          className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:border-slate-700 hover:text-cyan-400 transition-all duration-200"
          title="System Settings"
          aria-label="Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
