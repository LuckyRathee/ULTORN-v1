"use client";

import React, { useRef, useEffect } from "react";
import { Send, CornerDownLeft, Sparkles, Radio, CloudSun, Calendar, ListTodo, Zap } from "lucide-react";
import { soundSynth } from "@/utils/audioSynthesizer";

interface ConsoleInputProps {
  input: string;
  setInput: (val: string) => void;
  onSubmit: (text: string) => void;
  isProcessing: boolean;
  wakeWordEnabled: boolean;
  onToggleWakeWord: () => void;
}

const QUICK_PROMPTS = [
  { icon: CloudSun, label: "Weather in Tokyo", prompt: "What is the weather in Tokyo?" },
  { icon: Calendar, label: "Schedule Meeting", prompt: "Schedule a team sync meeting tomorrow at 3 PM" },
  { icon: ListTodo, label: "Create Task", prompt: "Add 'Review PR and deploy to production' to my Notion tasks" },
  { icon: Zap, label: "List Calendar", prompt: "List my calendar events for today" },
];

export const ConsoleInput: React.FC<ConsoleInputProps> = ({
  input,
  setInput,
  onSubmit,
  isProcessing,
  wakeWordEnabled,
  onToggleWakeWord,
}) => {
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Global Keyboard Focus Shortcut (Ctrl+K or /)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isProcessing) return;
    soundSynth.playClick();
    onSubmit(input.trim());
    setInput("");
  };

  return (
    <div className="w-full my-3 select-none">
      {/* Quick Prompt Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none mb-2 font-mono text-[11px]">
        <span className="text-slate-500 uppercase tracking-widest shrink-0">SUGGESTIONS:</span>
        {QUICK_PROMPTS.map((p) => {
          const Icon = p.icon;
          return (
            <button
              key={p.label}
              onClick={() => {
                soundSynth.playClick();
                setInput(p.prompt);
              }}
              className="px-2.5 py-1 rounded-full bg-slate-900/80 border border-slate-800 text-slate-300 hover:border-cyan-500/50 hover:text-cyan-300 transition-all duration-200 shrink-0 flex items-center gap-1.5"
            >
              <Icon className="w-3 h-3 text-cyan-400" />
              <span>{p.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Console Input Bar */}
      <form onSubmit={handleSubmit} className="relative flex items-center w-full">
        <div className="absolute left-3 sm:left-4 flex items-center gap-1.5 sm:gap-2 text-cyan-400 pointer-events-none">
          <Sparkles className="w-4 h-4 animate-pulse shrink-0" />
          <span className="font-mono text-xs text-slate-500 hidden sm:inline">ultron&gt;</span>
        </div>

        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter command... (Ctrl+K)"
          disabled={isProcessing}
          className="w-full pl-9 sm:pl-28 pr-20 sm:pr-32 py-3 sm:py-3.5 rounded-xl hud-card border border-slate-800 text-xs sm:text-sm font-mono text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/40 transition-all duration-200"
        />

        {/* Right Action & Wake Word Badges */}
        <div className="absolute right-3 flex items-center gap-2">
          {/* Wake Word Badge */}
          <button
            type="button"
            onClick={() => {
              soundSynth.playClick();
              onToggleWakeWord();
            }}
            className={`px-2 py-1 rounded text-[10px] font-mono flex items-center gap-1 transition-all ${
              wakeWordEnabled
                ? "bg-cyan-950/60 border border-cyan-500/40 text-cyan-400"
                : "bg-slate-900 border border-slate-800 text-slate-500"
            }`}
            title="Toggle Hands-free Wake Word ('ultron')"
          >
            <Radio className={`w-3 h-3 ${wakeWordEnabled ? "text-cyan-400 animate-pulse" : ""}`} />
            <span className="hidden sm:inline">"ultron" WAKE</span>
          </button>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className={`p-2 rounded-lg font-mono text-xs flex items-center gap-1 transition-all duration-200 ${
              input.trim() && !isProcessing
                ? "bg-cyan-600 text-white hover:bg-cyan-500 glow-cyan cursor-pointer"
                : "bg-slate-900 text-slate-600 cursor-not-allowed border border-slate-800"
            }`}
          >
            <Send className="w-4 h-4" />
            <CornerDownLeft className="w-3 h-3 hidden sm:inline" />
          </button>
        </div>
      </form>
    </div>
  );
};
