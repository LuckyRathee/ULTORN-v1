"use client";

import React, { useState } from "react";
import { Settings, X, Server, Radio, Volume2, Save, RefreshCw } from "lucide-react";
import { soundSynth } from "@/utils/audioSynthesizer";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  backendUrl: string;
  setBackendUrl: (url: string) => void;
  sessionId: string;
  setSessionId: (id: string) => void;
  wakeWordEnabled: boolean;
  setWakeWordEnabled: (val: boolean) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  backendUrl,
  setBackendUrl,
  sessionId,
  setSessionId,
  wakeWordEnabled,
  setWakeWordEnabled,
}) => {
  const [tempBackendUrl, setTempBackendUrl] = useState(backendUrl);
  const [tempSessionId, setTempSessionId] = useState(sessionId);
  const [tempWakeWord, setTempWakeWord] = useState(wakeWordEnabled);

  if (!isOpen) return null;

  const handleSave = () => {
    soundSynth.playSuccessBeep();
    setBackendUrl(tempBackendUrl);
    setSessionId(tempSessionId);
    setWakeWordEnabled(tempWakeWord);
    localStorage.setItem("ultron_session_id", tempSessionId);
    localStorage.setItem("ultron_wake_word_enabled", tempWakeWord.toString());
    onClose();
  };

  const handleGenerateSession = () => {
    soundSynth.playClick();
    const newSession = "session_" + Math.random().toString(36).substring(2, 11);
    setTempSessionId(newSession);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md font-mono select-none">
      <div className="w-full max-w-md rounded-xl hud-card p-6 border border-cyan-500/40 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-widest font-hud">
              SYSTEM CONFIGURATION
            </h3>
          </div>
          <button
            onClick={() => {
              soundSynth.playClick();
              onClose();
            }}
            className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Configuration Options */}
        <div className="space-y-4 text-xs">
          {/* Backend URL */}
          <div>
            <label className="block text-slate-400 mb-1 flex items-center gap-1.5 font-bold">
              <Server className="w-3.5 h-3.5 text-cyan-400" />
              FASTAPI BACKEND URL:
            </label>
            <input
              type="text"
              value={tempBackendUrl}
              onChange={(e) => setTempBackendUrl(e.target.value)}
              className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-cyan-300 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Session ID */}
          <div>
            <label className="block text-slate-400 mb-1 font-bold">SESSION IDENTIFIER:</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={tempSessionId}
                onChange={(e) => setTempSessionId(e.target.value)}
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-cyan-500"
              />
              <button
                type="button"
                onClick={handleGenerateSession}
                className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-cyan-400"
                title="Generate New Session"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Wake Word Switch */}
          <div className="flex items-center justify-between p-3 rounded bg-slate-950 border border-slate-800">
            <div>
              <div className="font-bold text-white flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-amber-400" />
                HANDS-FREE WAKE WORD ("ultron")
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">
                Uses Web Speech API browser engine
              </div>
            </div>
            <button
              type="button"
              onClick={() => setTempWakeWord(!tempWakeWord)}
              className={`w-12 h-6 rounded-full transition-colors p-1 relative ${
                tempWakeWord ? "bg-cyan-600" : "bg-slate-800"
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-white transition-transform ${
                  tempWakeWord ? "translate-x-6" : "translate-x-0"
                }`}
              />
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
          <button
            onClick={() => {
              soundSynth.playClick();
              onClose();
            }}
            className="px-4 py-2 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white text-xs"
          >
            CANCEL
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs flex items-center gap-1.5 glow-cyan"
          >
            <Save className="w-4 h-4" />
            SAVE CONFIGURATION
          </button>
        </div>
      </div>
    </div>
  );
};
