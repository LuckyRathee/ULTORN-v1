"use client";

import React, { useEffect, useRef } from "react";
import { Mic, Square, Volume2, Sparkles, Loader2, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { soundSynth } from "@/utils/audioSynthesizer";

interface PulsarCoreProps {
  status: "idle" | "recording" | "processing" | "playing" | "error";
  recordingTime: number;
  micVolume: number; // 0 to 1
  onStartRecording: () => void;
  onStopRecording: () => void;
  wakeWordStatus: "listening" | "detected" | "disabled" | "unsupported";
  wakeWordTranscript?: string;
  errorMessage?: string;
}

export const PulsarCore: React.FC<PulsarCoreProps> = ({
  status,
  recordingTime,
  micVolume,
  onStartRecording,
  onStopRecording,
  wakeWordStatus,
  wakeWordTranscript,
  errorMessage,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Format recording timer: mm:ss
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // Audio Spectrum Frequency Bar Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    const barCount = 32;

    const renderSpectrum = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = 105;

      for (let i = 0; i < barCount; i++) {
        const angle = (i / barCount) * Math.PI * 2;
        // Dynamic frequency bar height based on micVolume or status
        const randomFactor = Math.sin(Date.now() * 0.005 + i) * 0.3 + 0.7;
        const heightMultiplier =
          status === "recording"
            ? Math.max(micVolume * 45 * randomFactor, 6)
            : status === "processing"
            ? Math.sin(Date.now() * 0.01 + i) * 15 + 18
            : status === "playing"
            ? Math.cos(Date.now() * 0.008 + i) * 20 + 12
            : 4;

        const x1 = centerX + Math.cos(angle) * radius;
        const y1 = centerY + Math.sin(angle) * radius;
        const x2 = centerX + Math.cos(angle) * (radius + heightMultiplier);
        const y2 = centerY + Math.sin(angle) * (radius + heightMultiplier);

        ctx.strokeStyle =
          status === "recording"
            ? `rgba(244, 63, 94, ${0.4 + heightMultiplier / 50})`
            : status === "processing"
            ? `rgba(245, 158, 11, ${0.4 + heightMultiplier / 50})`
            : status === "playing"
            ? `rgba(16, 185, 129, ${0.4 + heightMultiplier / 50})`
            : "rgba(6, 182, 212, 0.25)";

        ctx.lineWidth = 3;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      animId = requestAnimationFrame(renderSpectrum);
    };

    renderSpectrum();
    return () => cancelAnimationFrame(animId);
  }, [status, micVolume]);

  const handleMicClick = () => {
    soundSynth.playClick();
    if (status === "recording") {
      onStopRecording();
    } else if (status === "idle" || status === "error") {
      onStartRecording();
    }
  };

  return (
    <div className="relative flex flex-col items-center justify-center py-6 my-2 select-none">
      {/* Outer Rotating HUD Ring Container */}
      <div className="relative w-80 h-80 flex items-center justify-center">
        {/* Spectrum Canvas */}
        <canvas
          ref={canvasRef}
          width={320}
          height={320}
          className="absolute inset-0 w-full h-full pointer-events-none"
        />

        {/* Concentric Pulsar Rings (Framer Motion) */}
        <AnimatePresence>
          {status === "recording" && (
            <>
              <motion.div
                initial={{ scale: 0.8, opacity: 0.6 }}
                animate={{ scale: [1, 1.4, 1.8], opacity: [0.6, 0.3, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }}
                className="absolute w-56 h-56 rounded-full border-2 border-rose-500/60 pointer-events-none glow-crimson"
              />
              <motion.div
                initial={{ scale: 0.9, opacity: 0.8 }}
                animate={{ scale: [1, 1.25, 1.5], opacity: [0.8, 0.4, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeOut", delay: 0.3 }}
                className="absolute w-56 h-56 rounded-full border border-rose-400/40 pointer-events-none"
              />
            </>
          )}

          {status === "processing" && (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
              className="absolute w-64 h-64 rounded-full border-2 border-dashed border-amber-500/60 pointer-events-none"
            />
          )}

          {status === "playing" && (
            <motion.div
              animate={{ scale: [1, 1.08, 1] }}
              transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
              className="absolute w-60 h-60 rounded-full border border-emerald-500/50 pointer-events-none glow-emerald"
            />
          )}
        </AnimatePresence>

        {/* Fixed Futuristic HUD Border Ring */}
        <div
          className={`absolute w-56 h-56 rounded-full border transition-all duration-500 ${
            status === "recording"
              ? "border-rose-500/60 bg-rose-950/20 glow-crimson"
              : status === "processing"
              ? "border-amber-500/60 bg-amber-950/20 glow-amber"
              : status === "playing"
              ? "border-emerald-500/60 bg-emerald-950/20 glow-emerald"
              : status === "error"
              ? "border-red-600/70 bg-red-950/30"
              : "border-cyan-500/40 bg-cyan-950/10 glow-cyan"
          }`}
        />

        {/* Central Trigger Orb Button */}
        <button
          onClick={handleMicClick}
          disabled={status === "processing"}
          className={`relative z-10 w-40 h-40 rounded-full flex flex-col items-center justify-center gap-2 cursor-pointer transition-all duration-300 transform active:scale-95 focus:outline-none ${
            status === "recording"
              ? "bg-rose-600 text-white shadow-[0_0_50px_rgba(244,63,94,0.7)]"
              : status === "processing"
              ? "bg-amber-600/80 text-amber-100 cursor-not-allowed"
              : status === "playing"
              ? "bg-emerald-600 text-white shadow-[0_0_40px_rgba(16,185,129,0.6)]"
              : status === "error"
              ? "bg-red-700 text-white shadow-[0_0_30px_rgba(239,68,68,0.6)]"
              : "bg-cyan-600/90 text-white hover:bg-cyan-500 hover:shadow-[0_0_45px_rgba(6,182,212,0.8)] glow-cyan"
          }`}
          title={
            status === "recording"
              ? "Click to stop & send voice command"
              : status === "processing"
              ? "ultron is executing pipeline..."
              : "Click to start recording voice command"
          }
        >
          {status === "recording" ? (
            <>
              <Square className="w-10 h-10 animate-pulse fill-white" />
              <span className="font-mono text-xs tracking-wider font-bold">
                {formatTime(recordingTime)}
              </span>
            </>
          ) : status === "processing" ? (
            <>
              <Loader2 className="w-10 h-10 animate-spin" />
              <span className="font-mono text-[11px] tracking-widest uppercase">PROCESSING</span>
            </>
          ) : status === "playing" ? (
            <>
              <Volume2 className="w-10 h-10 animate-bounce" />
              <span className="font-mono text-[11px] tracking-widest uppercase">SPEAKING</span>
            </>
          ) : status === "error" ? (
            <>
              <AlertCircle className="w-10 h-10 text-white" />
              <span className="font-mono text-[10px] uppercase font-bold">RETRY MIC</span>
            </>
          ) : (
            <>
              <Mic className="w-11 h-11" />
              <span className="font-mono text-[11px] tracking-widest font-bold uppercase">
                LISTEN
              </span>
            </>
          )}
        </button>
      </div>

      {/* Voice Status Telemetry Banner */}
      <div className="mt-3 flex flex-col items-center gap-1 font-mono text-xs">
        {status === "recording" ? (
          <div className="flex items-center gap-2 text-rose-400 font-semibold text-glow-crimson">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
            LIVE RECORDING // VAD ACTIVE ({Math.round(micVolume * 100)}%)
          </div>
        ) : status === "processing" ? (
          <div className="flex items-center gap-2 text-amber-400 font-semibold">
            <Sparkles className="w-3.5 h-3.5 animate-spin" />
            EXTRACTING INTENT & EXECUTING PIPELINE...
          </div>
        ) : status === "playing" ? (
          <div className="flex items-center gap-2 text-emerald-400 font-semibold">
            <Volume2 className="w-3.5 h-3.5 animate-pulse" />
            PLAYING SYNTHESIZED RESPONSE
          </div>
        ) : errorMessage ? (
          <div className="text-red-400 text-center max-w-md text-[11px] bg-red-950/40 px-3 py-1 rounded border border-red-800/60">
            {errorMessage}
          </div>
        ) : (
          <div className="flex items-center gap-2 text-slate-400">
            {wakeWordStatus === "listening" ? (
              <span className="text-cyan-400 text-[11px] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                WAKE WORD ACTIVE: SAY <span className="font-bold underline text-white">"ultron"</span>
              </span>
            ) : wakeWordStatus === "detected" ? (
              <span className="text-emerald-400 font-bold text-[11px] animate-pulse">
                "ultron" DETECTED! LISTENING...
              </span>
            ) : (
              <span className="text-slate-500 text-[11px]">CLICK OR PRESS ENTER TO TALK</span>
            )}
          </div>
        )}

        {wakeWordTranscript && (
          <div className="text-[10px] text-cyan-300/70 max-w-sm truncate italic">
            "{wakeWordTranscript}"
          </div>
        )}
      </div>
    </div>
  );
};
