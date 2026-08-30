"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  ChevronRight,
  Code,
  FileText,
  AlertTriangle,
  X,
} from "lucide-react";

export interface StageResult {
  stage: string;
  status: "pending" | "running" | "success" | "failed" | "skipped";
  latency_ms: number;
  error?: string;
  input?: any;
  output?: any;
}

export interface PipelineRunData {
  run_id?: string;
  id?: string;
  stages?: StageResult[];
  total_latency_ms?: number;
  transcription?: any;
  intent?: any;
  action_result?: any;
  response_text?: string;
}

interface PipelineTrackerProps {
  currentRun: PipelineRunData | null;
  detailedRun: PipelineRunData | null;
  isProcessing: boolean;
}

const DEFAULT_STAGES = [
  { name: "audio_input", label: "AUDIO INPUT", desc: "WAV conversion" },
  { name: "transcription", label: "STT TRANSCRIPTION", desc: "Groq Whisper" },
  { name: "intent_extraction", label: "INTENT EXTRACTION", desc: "Llama3 tool-calling" },
  { name: "confirm_intent", label: "CONFIRM INTENT", desc: "Confidence check" },
  { name: "action_execution", label: "ACTION EXECUTION", desc: "Weather/Calendar/Tasks" },
  { name: "response", label: "RESPONSE FORMAT", desc: "Text formatting" },
  { name: "tts", label: "TTS SPEECH", desc: "ElevenLabs synth" },
];

export const PipelineTracker: React.FC<PipelineTrackerProps> = ({
  currentRun,
  detailedRun,
  isProcessing,
}) => {
  const [selectedStage, setSelectedStage] = useState<StageResult | null>(null);

  // Derive stages from detailedRun or construct from currentRun
  const stages: StageResult[] = detailedRun?.stages || [
    {
      stage: "audio_input",
      status: currentRun ? "success" : "pending",
      latency_ms: 12,
    },
    {
      stage: "transcription",
      status: currentRun?.transcription ? "success" : isProcessing ? "running" : "pending",
      latency_ms: currentRun?.transcription?.duration_ms || 320,
      output: currentRun?.transcription,
    },
    {
      stage: "intent_extraction",
      status: currentRun?.intent ? "success" : isProcessing ? "running" : "pending",
      latency_ms: 180,
      output: currentRun?.intent,
    },
    {
      stage: "confirm_intent",
      status: currentRun?.intent ? "success" : "pending",
      latency_ms: 5,
    },
    {
      stage: "action_execution",
      status: currentRun?.action_result
        ? currentRun.action_result.success !== false
          ? "success"
          : "failed"
        : "pending",
      latency_ms: currentRun?.action_result?.latency_ms || 210,
      output: currentRun?.action_result,
    },
    {
      stage: "response",
      status: currentRun?.response_text ? "success" : "pending",
      latency_ms: 15,
      output: { text: currentRun?.response_text },
    },
    {
      stage: "tts",
      status: currentRun ? "success" : "pending",
      latency_ms: 450,
    },
  ];

  return (
    <div className="w-full rounded-xl hud-card p-4 border border-slate-800 my-4 select-none">
      {/* Header bar */}
      <div className="flex items-center justify-between mb-3 font-mono text-xs border-b border-slate-800/80 pb-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-white font-bold tracking-wider uppercase font-hud">
            PIPELINE STATE MACHINE TELEMETRY
          </span>
        </div>

        <div className="flex items-center gap-3 text-[11px] text-slate-400">
          <span>TOTAL LATENCY:</span>
          <span className="text-cyan-400 font-bold font-mono">
            {currentRun?.total_latency_ms || detailedRun?.total_latency_ms || "--"} ms
          </span>
        </div>
      </div>

      {/* 7 Stage Flow Timeline */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
        {DEFAULT_STAGES.map((def, idx) => {
          const matchedStage = stages.find((s) => s.stage === def.name);
          const stStatus = matchedStage?.status || "pending";
          const latency = matchedStage?.latency_ms;

          return (
            <div
              key={def.name}
              onClick={() => matchedStage && setSelectedStage(matchedStage)}
              className={`relative p-2.5 rounded-lg border text-left cursor-pointer transition-all duration-200 ${
                stStatus === "success"
                  ? "bg-cyan-950/20 border-cyan-500/40 hover:border-cyan-400"
                  : stStatus === "running"
                  ? "bg-amber-950/30 border-amber-500/60 animate-pulse"
                  : stStatus === "failed"
                  ? "bg-rose-950/30 border-rose-500/60"
                  : "bg-slate-900/40 border-slate-800/80 opacity-60 hover:opacity-100"
              }`}
            >
              {/* Top Stage Header */}
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mb-1">
                <span>0{idx + 1}</span>
                {stStatus === "success" ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
                ) : stStatus === "running" ? (
                  <Loader2 className="w-3.5 h-3.5 text-amber-400 animate-spin" />
                ) : stStatus === "failed" ? (
                  <XCircle className="w-3.5 h-3.5 text-rose-400" />
                ) : (
                  <Clock className="w-3.5 h-3.5 text-slate-600" />
                )}
              </div>

              {/* Stage Name */}
              <div className="font-mono text-[11px] font-bold text-slate-200 truncate tracking-wide">
                {def.label}
              </div>
              <div className="text-[9px] font-mono text-slate-400 truncate">{def.desc}</div>

              {/* Bottom Latency */}
              <div className="mt-2 text-[10px] font-mono text-cyan-400/80 flex items-center justify-between border-t border-slate-800/60 pt-1">
                <span>{latency ? `${latency}ms` : "--"}</span>
                {matchedStage?.output && <Code className="w-3 h-3 text-cyan-400" />}
              </div>
            </div>
          );
        })}
      </div>

      {/* JSON Payload Inspector Modal */}
      {selectedStage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
          <div className="w-full max-w-xl rounded-xl hud-card p-5 border border-cyan-500/40 shadow-2xl relative">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2 font-mono">
                <Code className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-widest font-hud">
                  STAGE DIAGNOSTIC // {selectedStage.stage}
                </h3>
              </div>

              <button
                onClick={() => setSelectedStage(null)}
                className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span>STATUS:</span>
                <span className="font-bold text-cyan-400 uppercase">{selectedStage.status}</span>
              </div>
              <div className="flex items-center justify-between text-slate-400">
                <span>LATENCY:</span>
                <span className="text-white">{selectedStage.latency_ms} ms</span>
              </div>

              {selectedStage.error && (
                <div className="p-3 rounded bg-rose-950/40 border border-rose-800/60 text-rose-300">
                  <div className="font-bold mb-1">ERROR DIAGNOSTIC:</div>
                  <pre className="whitespace-pre-wrap text-[11px]">{selectedStage.error}</pre>
                </div>
              )}

              {selectedStage.input && (
                <div>
                  <div className="text-slate-400 mb-1">INPUT PAYLOAD:</div>
                  <pre className="p-3 rounded bg-slate-950 border border-slate-800 text-cyan-300 overflow-x-auto text-[11px]">
                    {JSON.stringify(selectedStage.input, null, 2)}
                  </pre>
                </div>
              )}

              {selectedStage.output && (
                <div>
                  <div className="text-slate-400 mb-1">OUTPUT PAYLOAD:</div>
                  <pre className="p-3 rounded bg-slate-950 border border-slate-800 text-emerald-300 overflow-x-auto text-[11px]">
                    {JSON.stringify(selectedStage.output, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="mt-5 text-right">
              <button
                onClick={() => setSelectedStage(null)}
                className="px-4 py-1.5 rounded bg-cyan-950 border border-cyan-500/50 text-cyan-300 text-xs font-mono hover:bg-cyan-900"
              >
                CLOSE DIAGNOSTIC
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
