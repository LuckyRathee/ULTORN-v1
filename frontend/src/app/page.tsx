"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Mic,
  Square,
  Volume2,
  VolumeX,
  RefreshCw,
  ListTodo,
  CloudSun,
  Calendar,
  History,
  CheckCircle,
  XCircle,
  Play,
  Clock,
  Server,
  CornerDownLeft,
  Settings,
  HelpCircle,
  AlertTriangle,
  ArrowRight,
  Database,
  Layers,
  Sparkles,
  Radio,
  Zap,
  MicOff
} from "lucide-react";

// Types
interface StageResult {
  stage: string;
  status: "pending" | "running" | "success" | "failed" | "skipped";
  latency_ms: number;
  error?: string;
  input?: any;
  output?: any;
}

interface PipelineRun {
  id: string;
  session_id: string;
  status: "running" | "done" | "failed";
  stages: StageResult[];
  created_at: string;
  completed_at?: string;
  total_latency_ms: number;
}

interface ProcessAudioResponse {
  run_id: string;
  status: string;
  response_text: string;
  audio_url?: string; // base64 encoded audio
  transcription?: {
    text: string;
    language?: string;
    confidence?: number;
    duration_ms?: number;
  };
  intent?: {
    type: string;
    confidence?: number;
  };
  action_result?: {
    success: boolean;
    data?: any;
    error?: string;
    error_type?: string;
    latency_ms?: number;
  };
  total_latency_ms: number;
}

export default function JarvisDashboard() {
  // App Settings
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [sessionId, setSessionId] = useState("");
  const [showSettings, setShowSettings] = useState(false);

  // Conversation States
  const [status, setStatus] = useState<"idle" | "recording" | "processing" | "playing" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [keyboardInput, setKeyboardInput] = useState("");

  // Wake Word Engine States
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [wakeWordStatus, setWakeWordStatus] = useState<"listening" | "detected" | "disabled" | "unsupported">("listening");
  const [wakeWordTranscript, setWakeWordTranscript] = useState<string>("");
  const [wakeWordTriggerCount, setWakeWordTriggerCount] = useState<number>(0);
  const recognitionRef = useRef<any>(null);

  // Current Pipeline Run State
  const [currentRun, setCurrentRun] = useState<ProcessAudioResponse | null>(null);
  const [detailedRun, setDetailedRun] = useState<PipelineRun | null>(null);
  const [activeStageIndex, setActiveStageIndex] = useState(-1);

  // Audio Recording Refs & States
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const [micVolume, setMicVolume] = useState(0);

  // Voice Activity Detection (VAD) Refs
  const hasSpokenRef = useRef(false);
  const lastSpeechTimeRef = useRef<number>(0);
  const recordingStartTimeRef = useRef<number>(0);
  const isAutoSubmittingRef = useRef(false);

  // History & Sidebar
  const [history, setHistory] = useState<PipelineRun[]>([]);
  const [selectedHistoryRun, setSelectedHistoryRun] = useState<PipelineRun | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Speech Wave Animation Ref
  const [waveAnimation, setWaveAnimation] = useState<number[]>(Array(15).fill(4));

  // Initialize Session ID & Wake Word preference
  useEffect(() => {
    let savedSession = localStorage.getItem("jarvis_session_id");
    if (!savedSession) {
      savedSession = "session_" + Math.random().toString(36).substring(2, 11);
      localStorage.setItem("jarvis_session_id", savedSession);
    }
    setSessionId(savedSession);

    const savedWakeWord = localStorage.getItem("jarvis_wake_word_enabled");
    if (savedWakeWord !== null) {
      setWakeWordEnabled(savedWakeWord === "true");
    }
  }, []);

  // Fetch History on Session Load
  useEffect(() => {
    if (sessionId) {
      fetchHistory();
    }
  }, [sessionId, backendUrl]);

  // Trigger Greeting on Mount
  useEffect(() => {
    const triggerGreeting = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/v1/greet`);
        if (res.ok) {
          const data = await res.json();
          setCurrentRun({
            run_id: "greeting",
            status: "done",
            response_text: data.response_text,
            audio_url: data.audio_url || undefined,
            total_latency_ms: 0,
          });
          
          if (data.audio_url) {
            setStatus("playing");
            playBase64Audio(data.audio_url);
          }
        }
      } catch (err) {
        console.error("Failed to fetch greeting:", err);
      }
    };
    
    if (sessionId) {
      triggerGreeting();
    }
  }, [sessionId, backendUrl]);

  // Audio Context cleanup helper
  const cleanupAudioContext = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setMicVolume(0);
  };

  // Play Futuristic Wake Word Activation Chime
  const playActivationChime = () => {
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioContextClass) return;
      const ctx = new AudioContextClass();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12); // A5
      gain.gain.setValueAtTime(0.18, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.25);
    } catch (e) {
      // Audio context policy fallback
    }
  };

  // Continuous Wake Word Detection Engine ("Hey Jarvis", "Hello Jarvis", "Hi Jarvis", "Ok Jarvis")
  useEffect(() => {
    if (typeof window === "undefined") return;

    const SpeechRecognitionClass = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionClass) {
      setWakeWordStatus("unsupported");
      return;
    }

    if (!wakeWordEnabled) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
        recognitionRef.current = null;
      }
      setWakeWordStatus("disabled");
      return;
    }

    // Only listen for wake word when assistant is in idle state
    if (status !== "idle") {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
        recognitionRef.current = null;
      }
      return;
    }

    let recognition: any = null;
    let isCancelled = false;

    const startWakeWordListener = () => {
      if (isCancelled || status !== "idle" || !wakeWordEnabled) return;

      try {
        recognition = new SpeechRecognitionClass();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";

        recognition.onstart = () => {
          if (!isCancelled) {
            setWakeWordStatus("listening");
          }
        };

        recognition.onresult = (event: any) => {
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript.trim().toLowerCase();
            setWakeWordTranscript(transcript);

            // Pattern matches: "hey jarvis", "hello jarvis", "hi jarvis", "ok jarvis", "okay jarvis", "yo jarvis", "jarvis"
            const WAKE_PATTERN = /\b(hey|hello|hi|ok|okay|yo)?\s*jarvis\b/i;
            if (WAKE_PATTERN.test(transcript)) {
              console.log("[Wake Word Triggered]:", transcript);
              setWakeWordStatus("detected");
              setWakeWordTriggerCount((prev) => prev + 1);
              playActivationChime();

              // Stop recognition immediately to release microphone
              try {
                recognition.stop();
              } catch (e) {}
              recognitionRef.current = null;

              // Automatically trigger full high-fidelity voice recording
              setTimeout(() => {
                startRecording();
              }, 120);
              return;
            }
          }
        };

        recognition.onerror = (event: any) => {
          // Ignore non-critical recognition events
          if (event.error !== "no-speech" && event.error !== "aborted") {
            console.warn("[WakeWord] Recognition status:", event.error);
          }
        };

        recognition.onend = () => {
          // Auto-restart if we remain in idle mode and wake-word is active
          if (!isCancelled && status === "idle" && wakeWordEnabled) {
            setTimeout(() => {
              startWakeWordListener();
            }, 300);
          }
        };

        recognition.start();
        recognitionRef.current = recognition;
      } catch (err) {
        console.warn("[WakeWord] Initialization warning:", err);
      }
    };

    startWakeWordListener();

    return () => {
      isCancelled = true;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
        recognitionRef.current = null;
      }
    };
  }, [status, wakeWordEnabled]);

  // Handle Recording Timer and Waveform Sim
  useEffect(() => {
    let waveInterval: NodeJS.Timeout;
    if (status === "recording") {
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } else if (status === "playing") {
      waveInterval = setInterval(() => {
        setWaveAnimation(
          Array(15)
            .fill(0)
            .map(() => Math.floor(Math.random() * 20) + 4)
        );
      }, 100);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setRecordingTime(0);
      setWaveAnimation(Array(15).fill(4));
      cleanupAudioContext();
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (waveInterval) clearInterval(waveInterval);
    };
  }, [status]);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/runs?session_id=${sessionId}&limit=20`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.runs || []);
      }
    } catch (err) {
      console.error("Failed to fetch history:", err);
    }
  };

  const fetchDetailedRun = async (runId: string) => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/runs/${runId}`);
      if (res.ok) {
        const data = await res.json();
        setDetailedRun(data);
        return data;
      }
    } catch (err) {
      console.error("Failed to fetch detailed run:", err);
    }
    return null;
  };

  // Start Recording
  const startRecording = async () => {
    // Stop any currently playing audio response
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    setErrorMessage("");
    setCurrentRun(null);
    setDetailedRun(null);
    audioChunksRef.current = [];
    hasSpokenRef.current = false;
    lastSpeechTimeRef.current = Date.now();
    recordingStartTimeRef.current = Date.now();
    isAutoSubmittingRef.current = false;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((track) => track.stop());
        await processAudioFile(audioBlob);
      };

      // Set up Web Audio API for true real-time level monitoring & Voice Activity Detection (VAD)
      try {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        const audioContext = new AudioContextClass();
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 64; // Small fft for fast response
        source.connect(analyser);

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        audioContextRef.current = audioContext;
        analyserRef.current = analyser;

        const updateVolume = () => {
          if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
            analyser.getByteFrequencyData(dataArray);
            
            // Calculate a frequency-based visualization for the 15 bars
            const newAnimation = [];
            let totalVal = 0;
            const step = Math.floor(bufferLength / 15) || 1;
            
            for (let i = 0; i < 15; i++) {
              const value = dataArray[i * step] || 0;
              totalVal += value;
              // Map 0-255 value to 4px - 32px height
              const height = 4 + (value / 255) * 28;
              newAnimation.push(height);
            }
            
            // Average volume for scaling/glowing the button
            const avg = totalVal / (15 * 255);
            setMicVolume(avg);
            setWaveAnimation(newAnimation);

            // Voice Activity Detection (VAD) Auto-Submit on Silence
            const now = Date.now();
            const SPEECH_THRESHOLD = 0.04; // Volume threshold for detecting human voice

            if (avg > SPEECH_THRESHOLD) {
              hasSpokenRef.current = true;
              lastSpeechTimeRef.current = now;
            } else {
              const recordingDuration = now - recordingStartTimeRef.current;
              // Once user has spoken and silence lasts for >= 1.2 seconds, automatically stop & submit!
              if (hasSpokenRef.current && recordingDuration > 800) {
                const silenceDuration = now - lastSpeechTimeRef.current;
                if (silenceDuration >= 1200 && !isAutoSubmittingRef.current) {
                  isAutoSubmittingRef.current = true;
                  console.log("[VAD] User finished speaking (silence >= 1.2s). Auto-submitting response...");
                  stopRecording();
                  return;
                }
              } else if (!hasSpokenRef.current && recordingDuration > 9000) {
                // If user activated mic but didn't speak for 9 seconds, auto cancel
                if (!isAutoSubmittingRef.current) {
                  isAutoSubmittingRef.current = true;
                  stopRecording();
                  return;
                }
              }
            }
            
            animationFrameRef.current = requestAnimationFrame(updateVolume);
          }
        };
        animationFrameRef.current = requestAnimationFrame(updateVolume);
      } catch (audioErr) {
        console.error("Failed to initialize AudioContext:", audioErr);
      }

      mediaRecorder.start(200);
      setStatus("recording");
    } catch (err: any) {
      console.error("Microphone access denied:", err);
      setErrorMessage("Microphone access denied. Please verify browser permissions.");
      setStatus("error");
    }
  };

  // Stop Recording & Trigger Processing
  const stopRecording = () => {
    if (mediaRecorderRef.current && status === "recording") {
      mediaRecorderRef.current.stop();
      setStatus("processing");
      cleanupAudioContext();
    }
  };

  // Simulated Frontend Stage Loader (For UI styling while backend request is active)
  const runSimulatedProgress = () => {
    setActiveStageIndex(0); // Audio Input
    const timers = [
      setTimeout(() => setActiveStageIndex(1), 800),  // Transcription
      setTimeout(() => setActiveStageIndex(2), 1600), // Intent Extraction
      setTimeout(() => setActiveStageIndex(3), 2400), // Action Exec
      setTimeout(() => setActiveStageIndex(4), 3000), // Response Formatting
    ];
    return timers;
  };

  // Send Audio File to Backend
  const processAudioFile = async (audioBlob: Blob) => {
    setStatus("processing");
    const progressTimers = runSimulatedProgress();

    try {
      const formData = new FormData();
      // Browser records webm/ogg. Backend will convert to wav using ffmpeg if needed.
      formData.append("file", audioBlob, "recording.webm");
      formData.append("session_id", sessionId);

      const response = await fetch(`${backendUrl}/api/v1/process-audio/file`, {
        method: "POST",
        body: formData,
      });

      // Clear the simulation timers
      progressTimers.forEach(clearTimeout);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.user_message || `Server responded with ${response.status}`);
      }

      const result: ProcessAudioResponse = await response.json();
      setCurrentRun(result);

      // Fetch Full Pipeline run (contains the exact stage latency) from Supabase
      const details = await fetchDetailedRun(result.run_id);
      setActiveStageIndex(-1);

      // Play audio response if available
      if (result.audio_url) {
        setStatus("playing");
        playBase64Audio(result.audio_url);
      } else {
        setStatus("idle");
      }

      fetchHistory(); // Refresh session history
    } catch (err: any) {
      console.error("Audio processing failed:", err);
      setErrorMessage(err.message || "An unexpected error occurred during audio processing.");
      setStatus("error");
      setActiveStageIndex(-1);
    }
  };

  // Play Base64 Audio Output
  const playBase64Audio = (base64Data: string) => {
    try {
      const audioUrl = `data:audio/mp3;base64,${base64Data}`;
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      audio.onended = () => {
        setStatus("idle");
        audioRef.current = null;
      };
      audio.onerror = (e) => {
        console.error("Audio playback error:", e);
        setStatus("idle");
      };
      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch((error) => {
          console.log("Autoplay was prevented by browser policy. Displaying text greeting instead.", error);
          setStatus("idle");
        });
      }
    } catch (err) {
      console.error("Failed to play audio:", err);
      setStatus("idle");
    }
  };

  // Submit Text Input instead of voice (convenient fall back testing)
  const submitTextInput = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyboardInput.trim() || status === "processing") return;

    const textQuery = keyboardInput.trim();
    setKeyboardInput("");
    setErrorMessage("");
    setCurrentRun(null);
    setDetailedRun(null);
    setStatus("processing");
    const progressTimers = runSimulatedProgress();

    try {
      // Mock audio conversion or handle query by sending to backend
      // Note: Backend process-audio expects audio. But since we want to support text-fallback, 
      // let's simulate sending it or handle it cleanly.
      // Wait, in this backend main.py only process-audio is defined!
      // But we can notify the user that we are using speech instead.
      // However, we can create a synthesized silent audio or warn that only voice is active.
      // Let's check if the backend has a text endpoint. No, main.py only has /process-audio.
      // So let's alert that this is a Voice-Only assistant and they should use the mic button!
      progressTimers.forEach(clearTimeout);
      setErrorMessage("Jarvis 2.0 is a voice-first system. Please click the Microphone button to speak!");
      setStatus("error");
      setActiveStageIndex(-1);
    } catch (err: any) {
      progressTimers.forEach(clearTimeout);
      setErrorMessage("Text submission failed. Please use microphone.");
      setStatus("error");
    }
  };

  // Format Helper
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  // Stage Meta info helper
  const getStageMeta = (stage: string) => {
    switch (stage) {
      case "audio_input":
        return { label: "Audio Validation", desc: "Format verification & base64 decode" };
      case "transcription":
        return { label: "Transcription (STT)", desc: "Groq Whisper audio to text" };
      case "intent_extraction":
        return { label: "Intent Parsing (LLM)", desc: "Parsing intent schema" };
      case "action_execution":
        return { label: "Action Execution", desc: "Routing to service integrations" };
      case "response":
        return { label: "TTS & Response", desc: "Formatting answer & synthesis" };
      default:
        return { label: stage, desc: "" };
    }
  };

  // Reset Session History
  const clearSession = () => {
    const newSession = "session_" + Math.random().toString(36).substring(2, 11);
    localStorage.setItem("jarvis_session_id", newSession);
    setSessionId(newSession);
    setCurrentRun(null);
    setDetailedRun(null);
    setHistory([]);
    setStatus("idle");
    setErrorMessage("");
  };

  const getStatusColor = (currentStatus: string) => {
    switch (currentStatus) {
      case "recording":
        return "from-red-500/20 to-red-950/20 border-red-500/50 text-red-400";
      case "processing":
        return "from-amber-500/20 to-amber-950/20 border-amber-500/50 text-amber-400";
      case "playing":
        return "from-blue-500/20 to-blue-950/20 border-blue-500/50 text-blue-400";
      case "error":
        return "from-rose-600/25 to-rose-950/20 border-rose-500/50 text-rose-400";
      default:
        return "from-slate-900 to-slate-950 border-slate-800 text-slate-400";
    }
  };

  return (
    <div className="flex flex-1 h-screen overflow-hidden bg-slate-950 text-slate-100 font-sans">
      
      {/* SIDEBAR: HISTORY & DETAILS */}
      {isSidebarOpen && (
        <aside className="w-80 border-r border-slate-900 bg-slate-950 flex flex-col flex-shrink-0 animate-fade-in">
          {/* Header */}
          <div className="p-4 border-b border-slate-900 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="h-5 w-5 text-indigo-400" />
              <h2 className="font-semibold text-sm tracking-wide uppercase text-slate-200">Session History</h2>
            </div>
            <button
              onClick={clearSession}
              title="Start New Session"
              className="p-1.5 rounded-md hover:bg-slate-900 text-slate-400 hover:text-slate-200 transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>

          {/* Session ID display */}
          <div className="px-4 py-2 bg-slate-900/30 border-b border-slate-900/50 text-[11px] text-slate-500 flex justify-between items-center font-mono">
            <span>Session: {sessionId}</span>
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          </div>

          {/* History List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {history.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-center text-slate-600">
                <HelpCircle className="h-8 w-8 mb-2 stroke-1" />
                <p className="text-xs">No voice runs recorded in this session yet.</p>
              </div>
            ) : (
              history.map((run) => (
                <button
                  key={run.id}
                  onClick={async () => {
                    const fullData = await fetchDetailedRun(run.id);
                    setSelectedHistoryRun(fullData);
                  }}
                  className={`w-full text-left p-3 rounded-lg border transition-all flex flex-col gap-1.5 ${
                    (detailedRun?.id === run.id || selectedHistoryRun?.id === run.id)
                      ? "bg-indigo-950/20 border-indigo-500/50 text-indigo-200"
                      : "bg-slate-900/40 border-slate-900 hover:bg-slate-900/70 hover:border-slate-800 text-slate-300"
                  }`}
                >
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-mono text-[10px] text-slate-500">
                      {new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded-[4px] text-[10px] uppercase font-semibold ${
                      run.status === "done" ? "bg-emerald-950/50 text-emerald-400" : "bg-rose-950/50 text-rose-400"
                    }`}>
                      {run.status}
                    </span>
                  </div>
                  <p className="text-xs font-medium truncate">
                    {run.stages?.find((s) => s.stage === "transcription")?.output?.text || "Audio query"}
                  </p>
                  <div className="flex justify-between items-center text-[10px] text-slate-500">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {run.total_latency_ms}ms
                    </span>
                    <span className="capitalize font-mono">
                      {run.stages?.find((s) => s.stage === "intent_extraction")?.output?.intent?.type || "unknown"}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Footer settings toggle */}
          <div className="p-3 border-t border-slate-900 bg-slate-950/50">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="w-full py-2 px-3 rounded-lg hover:bg-slate-900 text-xs text-slate-400 hover:text-slate-200 flex items-center justify-between transition-colors border border-slate-900/50"
            >
              <span className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Backend Configuration
              </span>
              <span className="text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-indigo-400 font-mono">
                {backendUrl.replace("http://", "")}
              </span>
            </button>
          </div>
        </aside>
      )}

      {/* MAIN MAIN PAGE */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Settings Overlay Panel */}
        {showSettings && (
          <div className="bg-slate-900 border-b border-slate-800 p-4 animate-slide-down">
            <div className="max-w-2xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h3 className="font-semibold text-sm text-slate-200">Backend API URL Configuration</h3>
                <p className="text-xs text-slate-500">Redirect requests if your FastAPI is running on a different port/IP.</p>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={backendUrl}
                  onChange={(e) => setBackendUrl(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 w-56 focus:outline-none focus:border-indigo-500 font-mono"
                  placeholder="http://localhost:8000"
                />
                <button
                  onClick={() => {
                    setShowSettings(false);
                    fetchHistory();
                  }}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
                >
                  Save & Connect
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TOP NAVBAR */}
        <header className="h-14 border-b border-slate-900 px-6 flex items-center justify-between bg-slate-950/70 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-1.5 rounded-lg hover:bg-slate-900 text-slate-400 hover:text-slate-200 transition-colors"
              title="Toggle Sidebar"
            >
              <History className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-2.5 rounded-full bg-indigo-500 animate-pulse"></div>
              <h1 className="font-bold text-sm tracking-widest text-slate-100 flex items-center gap-1.5">
                JARVIS <span className="text-indigo-400 font-medium text-[11px] tracking-normal font-mono px-1 bg-indigo-950/80 rounded border border-indigo-900">v2.0</span>
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-400">
            {/* Wake Word Status Badge in Header */}
            {wakeWordStatus !== "unsupported" && (
              <button
                onClick={() => {
                  const nextVal = !wakeWordEnabled;
                  setWakeWordEnabled(nextVal);
                  localStorage.setItem("jarvis_wake_word_enabled", String(nextVal));
                }}
                title={wakeWordEnabled ? "Click to disable Wake Word detection" : "Click to enable Wake Word detection"}
                className={`hidden sm:flex items-center gap-2 px-3 py-1 rounded-full border transition-all ${
                  wakeWordEnabled
                    ? "bg-indigo-950/40 border-indigo-500/40 text-indigo-300 hover:bg-indigo-900/40"
                    : "bg-slate-900/80 border-slate-800 text-slate-500 hover:text-slate-400 hover:border-slate-700"
                }`}
              >
                <Radio className={`h-3.5 w-3.5 ${wakeWordEnabled && status === "idle" ? "text-indigo-400 animate-pulse" : "text-slate-600"}`} />
                <span className="font-mono text-[10px]">
                  {wakeWordEnabled ? "WAKE WORD: ON" : "WAKE WORD: OFF"}
                </span>
              </button>
            )}

            <div className="hidden sm:flex items-center gap-2 bg-slate-900 px-3 py-1 rounded-full border border-slate-900">
              <Server className="h-3.5 w-3.5 text-emerald-500" />
              <span className="font-mono text-[10px]">FastAPI: OK</span>
            </div>
          </div>
        </header>

        {/* WORKSPACE CONTENT LAYOUT */}
        <div className="flex-1 max-w-4xl w-full mx-auto p-6 flex flex-col gap-6">
          
          {/* DISPLAY HISTORICAL SELECTED RUN SEPARATELY IF CLICKED */}
          {selectedHistoryRun && (
            <div className="bg-slate-900/30 border border-slate-900 rounded-xl p-4 flex flex-col gap-3 relative animate-fade-in">
              <button
                onClick={() => setSelectedHistoryRun(null)}
                className="absolute top-3 right-3 text-slate-500 hover:text-slate-300 text-xs"
              >
                ✕ Close Detail View
              </button>
              <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold">
                <History className="h-3.5 w-3.5" />
                <span>Viewing Historical Event Details</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-xs text-slate-500 uppercase tracking-wider font-semibold">User Query</h4>
                  <p className="text-sm font-medium mt-1">
                    "{selectedHistoryRun.stages.find((s) => s.stage === "transcription")?.output?.text || "Speech recorded"}"
                  </p>
                </div>
                <div>
                  <h4 className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Parsed Intent</h4>
                  <p className="text-sm font-mono mt-1 capitalize text-indigo-300">
                    {selectedHistoryRun.stages.find((s) => s.stage === "intent_extraction")?.output?.intent?.type || "unknown"}
                  </p>
                </div>
              </div>
              
              {/* Output Result widgets for Historical logs */}
              {selectedHistoryRun.stages.find((s) => s.stage === "action_execution")?.output && (
                <div className="border-t border-slate-900/50 pt-3">
                  <h4 className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-2">Service Response & Details</h4>
                  {renderActionResult(
                    selectedHistoryRun.stages.find((s) => s.stage === "intent_extraction")?.output?.intent?.type || "",
                    selectedHistoryRun.stages.find((s) => s.stage === "action_execution")?.output
                  )}
                </div>
              )}

              {/* Latency breakdown for history */}
              <div className="border-t border-slate-900/50 pt-3">
                <h4 className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-2">Stage Performance</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedHistoryRun.stages.map((stage, idx) => (
                    <div key={`${stage.stage}-${idx}`} className="bg-slate-900/60 border border-slate-900 px-2 py-1 rounded text-[11px] font-mono flex items-center gap-1.5 font-sans">
                      <span className="text-slate-400 capitalize">{stage.stage.replace("_", " ")}:</span>
                      <span className="text-indigo-400 font-bold">{stage.latency_ms}ms</span>
                    </div>
                  ))}
                  <div className="bg-indigo-950/30 border border-indigo-900 px-2 py-1 rounded text-[11px] font-mono flex items-center gap-1.5 ml-auto">
                    <span className="text-indigo-300">Total Latency:</span>
                    <span className="text-emerald-400 font-bold">{selectedHistoryRun.total_latency_ms}ms</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* MAIN CHAT VOICE ASSISTANT INTERFACE */}
          <div className="flex-1 flex flex-col justify-center items-center py-10 bg-slate-900/10 border border-slate-900/40 rounded-2xl p-8 backdrop-blur-sm">
            
            {/* Visualizer and Pulsing Voice Button */}
            <div className="flex flex-col items-center justify-center gap-6">
              
              {/* Pulsing ring under mic */}
              <div className="relative flex items-center justify-center">
                
                {status === "recording" && (
                  <span className="absolute h-36 w-36 rounded-full bg-red-600/30 animate-ping"></span>
                )}
                {status === "processing" && (
                  <span className="absolute h-36 w-36 rounded-full bg-amber-500/20 animate-spin border-4 border-dashed border-amber-500/40"></span>
                )}
                {status === "playing" && (
                  <span className="absolute h-36 w-36 rounded-full bg-indigo-500/20 border-2 border-indigo-500/30 animate-pulse"></span>
                )}

                {/* Primary Button */}
                <button
                  onClick={status === "recording" ? stopRecording : startRecording}
                  disabled={status === "processing"}
                  className={`h-28 w-28 rounded-full flex items-center justify-center shadow-2xl relative border-2 transition-all duration-300 focus:outline-none ${
                    status === "recording"
                      ? "bg-gradient-to-br from-red-600 to-rose-700 border-red-400 text-white hover:scale-105 active:scale-95 cursor-pointer"
                      : status === "processing"
                      ? "bg-slate-900 border-slate-800 text-slate-600 cursor-not-allowed"
                      : status === "playing"
                      ? "bg-gradient-to-br from-indigo-600 to-blue-700 border-indigo-400 text-white hover:scale-105 active:scale-95 cursor-pointer"
                      : "bg-gradient-to-br from-slate-900 to-slate-950 border-slate-800 hover:border-slate-700 text-indigo-400 hover:text-indigo-300 hover:scale-105 active:scale-95 cursor-pointer"
                  }`}
                  style={
                    status === "recording"
                      ? {
                          transform: `scale(${1 + micVolume * 0.2})`,
                          boxShadow: `0 0 ${20 + micVolume * 45}px rgba(239, 68, 68, ${0.4 + micVolume * 0.6})`,
                        }
                      : undefined
                  }
                >
                  {status === "recording" ? (
                    <Square className="h-10 w-10 fill-white" />
                  ) : status === "processing" ? (
                    <RefreshCw className="h-10 w-10 animate-spin" />
                  ) : status === "playing" ? (
                    <Volume2 className="h-11 w-11 animate-pulse" />
                  ) : (
                    <Mic className="h-11 w-11" />
                  )}
                </button>
              </div>

              {/* Status Message and Voice Soundwave Visualizer */}
              <div className="text-center flex flex-col gap-3 items-center">
                <div className={`px-4 py-1.5 rounded-full border text-xs font-semibold uppercase tracking-widest bg-gradient-to-r ${getStatusColor(status)}`}>
                  {status === "recording" && `RECORDING ${formatTime(recordingTime)} • Auto-submitting on pause`}
                  {status === "processing" && "Processing Pipeline stage..."}
                  {status === "playing" && "Speaking audio response"}
                  {status === "error" && "Error Encountered"}
                  {status === "idle" && "Click mic or say 'Hey Jarvis'"}
                </div>

                {/* Animated wave bars */}
                <div className="flex items-center justify-center gap-1 h-8 mt-1">
                  {waveAnimation.map((height, i) => (
                    <div
                      key={i}
                      style={{ height: `${height}px` }}
                      className={`w-1 rounded-full transition-all duration-100 ${
                        status === "recording"
                          ? "bg-red-500"
                          : status === "playing"
                          ? "bg-indigo-500"
                          : "bg-slate-800"
                      }`}
                    ></div>
                  ))}
                </div>

                {/* Wake Word Trigger Banner & Toggle */}
                <div className="mt-2 flex flex-col items-center gap-2">
                  {wakeWordStatus === "unsupported" ? (
                    <span className="text-[11px] text-slate-500">
                      Browser does not support continuous speech wake word. Use the Mic button.
                    </span>
                  ) : wakeWordEnabled ? (
                    <div className="flex items-center gap-2 bg-indigo-950/30 border border-indigo-500/30 px-3.5 py-1.5 rounded-full text-indigo-300 text-xs shadow-[0_0_15px_rgba(99,102,241,0.15)] animate-fade-in">
                      <Zap className="h-3.5 w-3.5 text-amber-400 animate-pulse" />
                      <span className="font-medium text-[11px]">
                        Say <span className="font-semibold text-white">"Hey Jarvis"</span>, <span className="font-semibold text-white">"Hello Jarvis"</span>, or <span className="font-semibold text-white">"Hi Jarvis"</span>
                      </span>
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        setWakeWordEnabled(true);
                        localStorage.setItem("jarvis_wake_word_enabled", "true");
                      }}
                      className="flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-indigo-400 transition-colors"
                    >
                      <MicOff className="h-3 w-3" />
                      <span>Wake word disabled. Click to enable hands-free detection.</span>
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Error Message banner */}
            {status === "error" && errorMessage && (
              <div className="mt-6 max-w-md w-full bg-rose-950/30 border border-rose-900/60 p-4 rounded-xl flex gap-3 text-rose-400 animate-slide-up text-xs">
                <AlertTriangle className="h-5 w-5 flex-shrink-0" />
                <div>
                  <h4 className="font-bold uppercase tracking-wider">Error Details</h4>
                  <p className="mt-1 leading-relaxed text-rose-300/90">{errorMessage}</p>
                </div>
              </div>
            )}

            {/* PIPELINE LIVE PROGRESS TRACKER (DURING PROCESSING) */}
            {status === "processing" && (
              <div className="mt-8 max-w-md w-full bg-slate-950/60 border border-slate-900 rounded-xl p-4 flex flex-col gap-3 animate-fade-in">
                <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider">
                  <Layers className="h-4 w-4" />
                  <span>Pipeline Execution Tracker</span>
                </div>
                <div className="flex flex-col gap-2.5">
                  {["audio_input", "transcription", "intent_extraction", "action_execution", "response"].map((stage, idx) => {
                    const meta = getStageMeta(stage);
                    const isActive = activeStageIndex === idx;
                    const isCompleted = activeStageIndex > idx;
                    return (
                      <div
                        key={stage}
                        className={`flex items-center gap-3 p-2.5 rounded-lg border transition-all ${
                          isActive
                            ? "bg-indigo-950/20 border-indigo-500/50 text-slate-100"
                            : isCompleted
                            ? "bg-slate-900/35 border-slate-900 text-slate-400"
                            : "bg-slate-950/10 border-transparent text-slate-600"
                        }`}
                      >
                        <div className={`h-4 w-4 rounded-full flex items-center justify-center text-[10px] ${
                          isActive
                            ? "bg-indigo-500 text-white animate-pulse"
                            : isCompleted
                            ? "bg-emerald-950 text-emerald-400"
                            : "bg-slate-900 text-slate-600"
                        }`}>
                          {isCompleted ? "✓" : idx + 1}
                        </div>
                        <div className="flex-1 text-left">
                          <p className="text-xs font-semibold capitalize">{meta.label}</p>
                          <p className="text-[10px] text-slate-500 mt-0.5 leading-none">{meta.desc}</p>
                        </div>
                        {isActive && (
                          <span className="text-[10px] text-indigo-400 font-mono animate-pulse">running</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* RESULTS VIEW (AFTER SUCCESSFUL PIPELINE RUN) */}
            {currentRun && status !== "processing" && (
              <div className="mt-8 w-full max-w-xl space-y-4 animate-slide-up">
                
                {/* User transcription text card */}
                {currentRun.transcription && (
                  <div className="bg-slate-950/80 border border-slate-900 rounded-xl p-4">
                    <h4 className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">What you said</h4>
                    <p className="text-base font-semibold text-slate-200 mt-1 italic">
                      "{currentRun.transcription.text}"
                    </p>
                  </div>
                )}

                {/* Assistant response text card */}
                <div className="bg-gradient-to-br from-indigo-950/10 to-slate-950/80 border border-indigo-900/30 rounded-xl p-5 shadow-lg">
                  <div className="flex justify-between items-center">
                    <h4 className="text-[10px] text-indigo-400 font-mono uppercase tracking-wider flex items-center gap-1.5">
                      <Sparkles className="h-3 w-3" />
                      Jarvis Response
                    </h4>
                    <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {currentRun.total_latency_ms}ms
                    </span>
                  </div>
                  <p className="text-base font-medium mt-2 leading-relaxed text-slate-100">
                    {currentRun.response_text}
                  </p>

                  {/* Play audio button again */}
                  {currentRun.audio_url && status !== "playing" && (
                    <button
                      onClick={() => {
                        setStatus("playing");
                        playBase64Audio(currentRun.audio_url!);
                      }}
                      className="mt-4 flex items-center gap-2 bg-indigo-900/30 hover:bg-indigo-900/50 border border-indigo-500/20 hover:border-indigo-500/40 text-indigo-300 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                    >
                      <Play className="h-3.5 w-3.5 fill-indigo-300" />
                      Replay Voice Response
                    </button>
                  )}
                </div>

                {/* Special Action Widget Renderer */}
                {currentRun.intent && currentRun.action_result && currentRun.action_result.success && (
                  <div className="bg-slate-950/60 border border-slate-900 rounded-xl p-4">
                    <h4 className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-3">Service Action output</h4>
                    {renderActionResult(currentRun.intent.type, currentRun.action_result.data)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* KEYBOARD QUICK FORM FALLBACK */}
          <form onSubmit={submitTextInput} className="flex gap-2 bg-slate-900/40 p-2.5 rounded-xl border border-slate-900 max-w-xl mx-auto w-full">
            <input
              type="text"
              value={keyboardInput}
              onChange={(e) => setKeyboardInput(e.target.value)}
              placeholder="Ask Jarvis anything (voice recording recommended)..."
              disabled={status === "processing"}
              className="flex-1 bg-transparent text-xs text-slate-300 px-2.5 py-2.5 focus:outline-none placeholder-slate-600 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={status === "processing"}
              className="bg-indigo-600/80 hover:bg-indigo-600 text-white rounded-lg px-4 py-2 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <span className="text-xs font-semibold">Send</span>
              <CornerDownLeft className="h-3.5 w-3.5" />
            </button>
          </form>
        </div>
      </main>
    </div>
  );

  // WIDGET RENDERING METHOD
  function renderActionResult(intentType: string, data: any) {
    if (!data) return null;

    // Weather widget
    if (intentType === "weather") {
      const location = data.location || "Unknown";
      const condition = data.condition || "Unknown";
      const temp = data.temperature;
      const humidity = data.humidity;
      const wind = data.wind_kph;
      const feelsLike = data.feels_like;

      return (
        <div className="bg-gradient-to-r from-slate-900 to-indigo-950/20 border border-slate-900 rounded-lg p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-lg bg-indigo-950/50 border border-indigo-900 flex items-center justify-center text-indigo-400">
              <CloudSun className="h-7 w-7" />
            </div>
            <div>
              <h5 className="text-sm font-semibold text-slate-200">{location}</h5>
              <p className="text-xs text-slate-400 capitalize">{condition}</p>
            </div>
          </div>
          <div className="flex gap-6 items-center">
            {temp !== undefined && (
              <div className="text-center">
                <span className="text-3xl font-extrabold tracking-tighter text-slate-100">{temp}°C</span>
                <p className="text-[10px] text-slate-500 font-mono uppercase mt-0.5">Temp</p>
              </div>
            )}
            <div className="h-8 w-[1px] bg-slate-900"></div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <div className="text-slate-400">Feels Like: <span className="font-semibold text-slate-200">{feelsLike ?? temp}°C</span></div>
              <div className="text-slate-400">Humidity: <span className="font-semibold text-slate-200">{humidity}%</span></div>
              <div className="text-slate-400 col-span-2">Wind Speed: <span className="font-semibold text-slate-200">{wind} km/h</span></div>
            </div>
          </div>
        </div>
      );
    }

    // Notion Task Create widget
    if (intentType === "task_create") {
      return (
        <div className="bg-slate-900/40 border border-slate-900 p-3 rounded-lg flex items-center gap-3 animate-fade-in">
          <div className="h-9 w-9 rounded-lg bg-emerald-950/50 border border-emerald-900/50 flex items-center justify-center text-emerald-400">
            <ListTodo className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[10px] text-emerald-400 font-mono uppercase tracking-wider font-semibold">Notion Task Created</span>
            <h5 className="text-sm font-semibold text-slate-200 mt-0.5">"{data.title}"</h5>
          </div>
        </div>
      );
    }

    // Notion Tasks List widget
    if (intentType === "task_list") {
      const tasks = data.tasks || [];
      if (tasks.length === 0) {
        return (
          <div className="text-xs text-slate-500 p-2 text-center">
            No pending tasks found in Notion database.
          </div>
        );
      }
      return (
        <div className="flex flex-col gap-2 animate-fade-in max-h-60 overflow-y-auto pr-1">
          {tasks.map((task: any, index: number) => (
            <div
              key={task.id || index}
              className="bg-slate-900/40 border border-slate-900 p-2.5 rounded-lg flex items-center justify-between gap-3"
            >
              <div className="flex items-center gap-2.5">
                <input
                  type="checkbox"
                  checked={task.completed}
                  readOnly
                  className="rounded border-slate-800 bg-slate-950 text-indigo-500 focus:ring-0 focus:ring-offset-0 h-4 w-4"
                />
                <div>
                  <h5 className={`text-xs font-semibold text-slate-200 ${task.completed ? "line-through text-slate-500" : ""}`}>
                    {task.title}
                  </h5>
                  {task.due_date && (
                    <p className="text-[10px] text-slate-500 font-mono mt-0.5">Due: {task.due_date}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-mono font-bold ${
                  task.priority === "high"
                    ? "bg-rose-950/60 text-rose-400 border border-rose-900/45"
                    : task.priority === "medium"
                    ? "bg-amber-950/40 text-amber-400 border border-amber-900/35"
                    : "bg-slate-850 text-slate-400 border border-slate-900"
                }`}>
                  {task.priority || "medium"}
                </span>
              </div>
            </div>
          ))}
        </div>
      );
    }

    // Google Calendar Create
    if (intentType === "calendar_create") {
      return (
        <div className="bg-slate-900/40 border border-slate-900 p-3 rounded-lg flex items-center gap-3 animate-fade-in">
          <div className="h-9 w-9 rounded-lg bg-indigo-950/50 border border-indigo-900/50 flex items-center justify-center text-indigo-400">
            <Calendar className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[10px] text-indigo-400 font-mono uppercase tracking-wider font-semibold">Calendar Event Created</span>
            <h5 className="text-sm font-semibold text-slate-200 mt-0.5">"{data.title}"</h5>
            {data.start_time && (
              <p className="text-[10px] text-slate-500 font-mono mt-0.5">Scheduled for: {data.start_time}</p>
            )}
          </div>
        </div>
      );
    }

    // Google Calendar List
    if (intentType === "calendar_list") {
      const events = data.events || [];
      if (events.length === 0) {
        return (
          <div className="text-xs text-slate-500 p-2 text-center">
            No upcoming events found.
          </div>
        );
      }
      return (
        <div className="flex flex-col gap-2 animate-fade-in max-h-60 overflow-y-auto pr-1">
          {events.map((evt: any, idx: number) => (
            <div
              key={idx}
              className="bg-slate-900/40 border border-slate-900 p-2.5 rounded-lg flex items-center justify-between gap-3"
            >
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-indigo-950/40 border border-indigo-950 flex flex-col items-center justify-center text-indigo-400">
                  <Calendar className="h-4 w-4" />
                </div>
                <div>
                  <h5 className="text-xs font-semibold text-slate-200">{evt.title}</h5>
                  <p className="text-[10px] text-slate-500 font-mono mt-0.5">{evt.start_time}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      );
    }

    // Generic display for nested payload response
    return (
      <pre className="text-[10px] bg-slate-950 p-3 rounded-lg overflow-x-auto text-slate-400 font-mono leading-relaxed max-h-48">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  }
}
