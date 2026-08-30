"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Volume2,
  VolumeX,
  Play,
  Pause,
  CloudSun,
  Calendar,
  ListTodo,
  Activity,
  Sparkles,
  Database,
  CheckCircle2,
  Clock,
  ArrowRight,
  ExternalLink,
  Layers,
  Thermometer,
  Wind,
  Droplets,
  Plus,
} from "lucide-react";
import { soundSynth } from "@/utils/audioSynthesizer";

interface UltronWidgetsProps {
  currentRun: any;
  backendUrl: string;
  onSendPrompt: (prompt: string) => void;
}

export const UltronWidgets: React.FC<UltronWidgetsProps> = ({
  currentRun,
  backendUrl,
  onSendPrompt,
}) => {
  const [activeTab, setActiveTab] = useState<"overview" | "weather" | "calendar" | "tasks" | "system">("overview");

  // Audio Response Player States
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioSpeed, setAudioSpeed] = useState(1);
  const [typedResponse, setTypedResponse] = useState("");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Sample/Real Weather Data
  const weatherData = currentRun?.action_result?.data?.weather || {
    city: "New York",
    temp_c: 22,
    condition: "Partly Cloudy",
    humidity: 55,
    wind_kph: 14.5,
  };

  // Typing Effect for Response Text
  useEffect(() => {
    const text = currentRun?.response_text || "ultron 2.0 system active. Ready for voice or text commands.";
    setTypedResponse("");
    let i = 0;

    const timer = setInterval(() => {
      if (i < text.length) {
        setTypedResponse((prev) => prev + text.charAt(i));
        i++;
      } else {
        clearInterval(timer);
      }
    }, 12);

    return () => clearInterval(timer);
  }, [currentRun?.response_text]);

  // Handle Base64 Audio Playback
  useEffect(() => {
    if (currentRun?.audio_url) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const audio = new Audio(`data:audio/mp3;base64,${currentRun.audio_url}`);
      audioRef.current = audio;
      audio.playbackRate = audioSpeed;
      audio.play().then(() => setIsPlaying(true)).catch(() => {});

      audio.onended = () => setIsPlaying(false);
    }
  }, [currentRun?.audio_url]);

  const togglePlayAudio = () => {
    soundSynth.playClick();
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const changeSpeed = () => {
    soundSynth.playClick();
    const newSpeed = audioSpeed === 1 ? 1.25 : audioSpeed === 1.25 ? 1.5 : 1;
    setAudioSpeed(newSpeed);
    if (audioRef.current) {
      audioRef.current.playbackRate = newSpeed;
    }
  };

  return (
    <div className="w-full my-4 select-none">
      {/* Tab Navigation */}
      <div className="flex items-center gap-1.5 sm:gap-2 border-b border-slate-800 pb-2 mb-4 font-mono text-xs overflow-x-auto scrollbar-none touch-pan-x w-full">
        <button
          onClick={() => {
            soundSynth.playClick();
            setActiveTab("overview");
          }}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all shrink-0 ${
            activeTab === "overview"
              ? "bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 glow-cyan"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>RESPONSE & TELEMETRY</span>
        </button>

        <button
          onClick={() => {
            soundSynth.playClick();
            setActiveTab("weather");
          }}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all shrink-0 ${
            activeTab === "weather"
              ? "bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 glow-cyan"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <CloudSun className="w-3.5 h-3.5 text-amber-400" />
          <span>WEATHER STATION</span>
        </button>

        <button
          onClick={() => {
            soundSynth.playClick();
            setActiveTab("calendar");
          }}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all shrink-0 ${
            activeTab === "calendar"
              ? "bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 glow-cyan"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Calendar className="w-3.5 h-3.5 text-emerald-400" />
          <span>CALENDAR AGENDA</span>
        </button>

        <button
          onClick={() => {
            soundSynth.playClick();
            setActiveTab("tasks");
          }}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all shrink-0 ${
            activeTab === "tasks"
              ? "bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 glow-cyan"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <ListTodo className="w-3.5 h-3.5 text-rose-400" />
          <span>NOTION TASK MATRIX</span>
        </button>

        <button
          onClick={() => {
            soundSynth.playClick();
            setActiveTab("system");
          }}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all shrink-0 ${
            activeTab === "system"
              ? "bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 glow-cyan"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Activity className="w-3.5 h-3.5 text-purple-400" />
          <span>SYS DIAGNOSTICS</span>
        </button>
      </div>

      {/* Tab 1: Live Response & Audio Synthesizer */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Main Response Output Card */}
          <div className="lg:col-span-2 rounded-xl hud-card p-5 border border-slate-800">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-3">
              <div className="flex items-center gap-2 font-mono text-xs">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-white font-bold tracking-wider uppercase font-hud">
                  ultron AI SPEECH OUTPUT
                </span>
              </div>

              {currentRun?.audio_url && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={togglePlayAudio}
                    className="px-2.5 py-1 rounded bg-cyan-950 border border-cyan-500/40 text-cyan-300 text-xs font-mono flex items-center gap-1 hover:bg-cyan-900"
                  >
                    {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                    <span>{isPlaying ? "PAUSE" : "REPLAY AUDIO"}</span>
                  </button>

                  <button
                    onClick={changeSpeed}
                    className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 text-xs font-mono hover:text-cyan-400"
                  >
                    {audioSpeed}x
                  </button>
                </div>
              )}
            </div>

            {/* Typing Response Text */}
            <div className="min-h-[90px] font-mono text-sm leading-relaxed text-cyan-100 bg-slate-950/60 p-4 rounded-lg border border-slate-800/80 relative">
              {typedResponse || "Awaiting audio command..."}
              <span className="inline-block w-2 h-4 bg-cyan-400 ml-1 animate-pulse" />
            </div>

            {/* Extracted Intent Badge */}
            {currentRun?.intent && (
              <div className="mt-3 flex items-center gap-2 font-mono text-xs text-slate-400">
                <span>INTENT:</span>
                <span className="px-2 py-0.5 rounded bg-cyan-950 border border-cyan-500/30 text-cyan-300 font-bold uppercase">
                  {currentRun.intent.type || "WEATHER_INTENT"}
                </span>
                <span className="text-slate-500">
                  (Confidence: {Math.round((currentRun.intent.confidence || 0.95) * 100)}%)
                </span>
              </div>
            )}
          </div>

          {/* Quick Telemetry Summary */}
          <div className="rounded-xl hud-card p-5 border border-slate-800 flex flex-col justify-between font-mono">
            <div>
              <div className="text-xs font-bold text-slate-300 uppercase tracking-widest border-b border-slate-800 pb-2 mb-3 font-hud">
                LIVE METRICS
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>RUN ID:</span>
                  <span className="text-cyan-300">{currentRun?.run_id || "N/A"}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>STT MODEL:</span>
                  <span className="text-white font-semibold">WHISPER (GROQ)</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>LLM ROUTER:</span>
                  <span className="text-amber-300">LLAMA3-70B</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>PERSISTENCE:</span>
                  <span className="text-emerald-400">SUPABASE LOGGED</span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-500">
              ⚡ Hardware acceleration: ON // hardware-transforms enabled
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Weather Station Widget */}
      {activeTab === "weather" && (
        <div className="rounded-xl hud-card p-5 border border-slate-800 font-mono">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <CloudSun className="w-5 h-5 text-amber-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-widest font-hud">
                WEATHER TELEMETRY STATION
              </h3>
            </div>
            <button
              onClick={() => onSendPrompt("What is the weather in Tokyo?")}
              className="text-xs text-cyan-400 hover:underline flex items-center gap-1"
            >
              REFRESH TELEMETRY <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 flex items-center gap-3">
              <Thermometer className="w-8 h-8 text-amber-400" />
              <div>
                <div className="text-2xl font-bold text-white">{weatherData.temp_c}°C</div>
                <div className="text-xs text-slate-400">{weatherData.condition}</div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 flex items-center gap-3">
              <Wind className="w-8 h-8 text-cyan-400" />
              <div>
                <div className="text-lg font-bold text-white">{weatherData.wind_kph} km/h</div>
                <div className="text-xs text-slate-400">Wind Velocity</div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 flex items-center gap-3">
              <Droplets className="w-8 h-8 text-blue-400" />
              <div>
                <div className="text-lg font-bold text-white">{weatherData.humidity}%</div>
                <div className="text-xs text-slate-400">Relative Humidity</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Calendar Agenda Widget */}
      {activeTab === "calendar" && (
        <div className="rounded-xl hud-card p-5 border border-slate-800 font-mono">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-emerald-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-widest font-hud">
                GOOGLE CALENDAR AGENDA
              </h3>
            </div>
            <button
              onClick={() => onSendPrompt("List my calendar events for today")}
              className="text-xs text-cyan-400 hover:underline flex items-center gap-1"
            >
              FETCH EVENTS <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-2">
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Clock className="w-4 h-4 text-emerald-400" />
                <div>
                  <div className="text-xs font-bold text-white">ultron Architecture Sync</div>
                  <div className="text-[10px] text-slate-400">14:00 - 15:00 UTC // Google Meet</div>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 text-[10px]">
                CONFIRMED
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Clock className="w-4 h-4 text-emerald-400" />
                <div>
                  <div className="text-xs font-bold text-white">Frontend UI/UX Review</div>
                  <div className="text-[10px] text-slate-400">16:30 - 17:30 UTC // Cockpit Demo</div>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 text-[10px]">
                UPCOMING
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Notion Task Matrix Widget */}
      {activeTab === "tasks" && (
        <div className="rounded-xl hud-card p-5 border border-slate-800 font-mono">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <ListTodo className="w-5 h-5 text-rose-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-widest font-hud">
                NOTION TASK MATRIX
              </h3>
            </div>
            <button
              onClick={() => onSendPrompt("Add 'Review PR and deploy' to Notion tasks")}
              className="text-xs text-cyan-400 hover:underline flex items-center gap-1"
            >
              + QUICK TASK <Plus className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-2">
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-xs text-slate-300 line-through">
                  Implement Supabase persistence logger
                </span>
              </div>
              <span className="text-[10px] text-slate-500">PRIORITY: HIGH</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                <span className="text-xs text-white font-semibold">
                  UI/UX Pro Max HUD Cockpit GUI Overhaul
                </span>
              </div>
              <span className="text-[10px] text-rose-400 font-bold">IN PROGRESS</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: System Telemetry Panel */}
      {activeTab === "system" && (
        <div className="rounded-xl hud-card p-5 border border-slate-800 font-mono">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-purple-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-widest font-hud">
                SYSTEM DIAGNOSTICS & LOGS
              </h3>
            </div>
            <span className="text-xs text-emerald-400">ALL SYSTEMS NOMINAL</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-3 rounded bg-slate-950 border border-slate-800">
              <div className="text-slate-400 mb-2 font-bold">STAGE LATENCY MATRIX</div>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span>Audio Stage:</span>
                  <span className="text-cyan-400">12ms</span>
                </div>
                <div className="flex justify-between">
                  <span>Whisper STT:</span>
                  <span className="text-cyan-400">320ms</span>
                </div>
                <div className="flex justify-between">
                  <span>Llama3 Intent:</span>
                  <span className="text-cyan-400">180ms</span>
                </div>
                <div className="flex justify-between">
                  <span>WeatherAPI / Action:</span>
                  <span className="text-cyan-400">210ms</span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded bg-slate-950 border border-slate-800">
              <div className="text-slate-400 mb-2 font-bold">DATABASE CONNECTIVITY</div>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span>Supabase Runs:</span>
                  <span className="text-emerald-400">CONNECTED</span>
                </div>
                <div className="flex justify-between">
                  <span>FastAPI Engine:</span>
                  <span className="text-emerald-400">PORT 8000</span>
                </div>
                <div className="flex justify-between">
                  <span>Web Audio API:</span>
                  <span className="text-emerald-400">ACTIVE</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
