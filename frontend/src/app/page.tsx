"use client";

import React, { useState, useEffect, useRef } from "react";
import { SciFiBackground } from "@/components/ui/SciFiBackground";
import { HudHeader } from "@/components/ui/HudHeader";
import { PulsarCore } from "@/components/ui/PulsarCore";
import { PipelineTracker } from "@/components/ui/PipelineTracker";
import { ConsoleInput } from "@/components/ui/ConsoleInput";
import { UltronWidgets } from "@/components/ui/UltronWidgets";
import { TelemetrySidebar } from "@/components/ui/TelemetrySidebar";
import { SettingsModal } from "@/components/ui/SettingsModal";
import { soundSynth } from "@/utils/audioSynthesizer";

export default function ultronDashboard() {
  // Application Settings
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [sessionId, setSessionId] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);

  // Status & Telemetry
  const [status, setStatus] = useState<"idle" | "recording" | "processing" | "playing" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [inputCommand, setInputCommand] = useState("");

  // Audio Recording & VAD
  const [recordingTime, setRecordingTime] = useState(0);
  const [micVolume, setMicVolume] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Wake Word Engine
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [wakeWordStatus, setWakeWordStatus] = useState<"listening" | "detected" | "disabled" | "unsupported">("listening");
  const [wakeWordTranscript, setWakeWordTranscript] = useState("");
  const recognitionRef = useRef<any>(null);

  // Pipeline Runs & History
  const [currentRun, setCurrentRun] = useState<any>(null);
  const [detailedRun, setDetailedRun] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Initialize Session ID & Storage Preferences
  useEffect(() => {
    let savedSession = localStorage.getItem("ultron_session_id");
    if (!savedSession) {
      savedSession = "session_" + Math.random().toString(36).substring(2, 11);
      localStorage.setItem("ultron_session_id", savedSession);
    }
    setSessionId(savedSession);

    const savedWakeWord = localStorage.getItem("ultron_wake_word_enabled");
    if (savedWakeWord !== null) {
      setWakeWordEnabled(savedWakeWord === "true");
    }
  }, []);

  // Sync sound toggle to sound synth
  const handleToggleSound = () => {
    const nextVal = !soundEnabled;
    setSoundEnabled(nextVal);
    soundSynth.setSoundEnabled(nextVal);
  };

  // Fetch Telemetry History from Supabase Backend
  const fetchHistory = async () => {
    if (!sessionId) return;
    try {
      const res = await fetch(`${backendUrl}/api/v1/runs?session_id=${sessionId}&limit=20`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.runs || []);
      }
    } catch (err) {
      console.warn("Failed to fetch pipeline runs:", err);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [sessionId, backendUrl]);

  // Wake Word Recognition Listener
  useEffect(() => {
    if (!wakeWordEnabled || status === "recording" || status === "processing") {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
      setWakeWordStatus(wakeWordEnabled ? "listening" : "disabled");
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setWakeWordStatus("unsupported");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onresult = (event: any) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }

        setWakeWordTranscript(transcript);

        if (transcript.toLowerCase().includes("ultron")) {
          setWakeWordStatus("detected");
          soundSynth.playActivationChime();
          startRecording();
          try {
            recognition.stop();
          } catch (e) {}
        }
      };

      recognition.onerror = () => {
        setTimeout(() => {
          if (wakeWordEnabled && status === "idle") {
            try {
              recognition.start();
            } catch (e) {}
          }
        }, 2000);
      };

      recognition.start();
      recognitionRef.current = recognition;
      setWakeWordStatus("listening");
    } catch (err) {
      console.warn("Speech recognition error:", err);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
    };
  }, [wakeWordEnabled, status]);

  // Audio Analyzer Cleanup
  const cleanupAudioContext = () => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setMicVolume(0);
  };

  // Start Voice Recording
  const startRecording = async () => {
    try {
      setErrorMessage("");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Web Audio API Analyzer for Volume Reactivity
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioContextClass) {
        const audioCtx = new AudioContextClass();
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;
        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);

        audioContextRef.current = audioCtx;
        analyserRef.current = analyser;

        const updateVolume = () => {
          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          setMicVolume(avg / 255);
          animFrameRef.current = requestAnimationFrame(updateVolume);
        };
        updateVolume();
      }

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        cleanupAudioContext();
        stream.getTracks().forEach((track) => track.stop());

        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        await processAudio(audioBlob);
      };

      mediaRecorder.start(100);
      setStatus("recording");
      setRecordingTime(0);

      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err: any) {
      console.error("Microphone access failed:", err);
      setErrorMessage("Microphone permission denied or not available.");
      setStatus("error");
      soundSynth.playErrorAlert();
    }
  };

  // Stop Voice Recording
  const stopRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  };

  // Submit Text Command Prompt
  const handleTextSubmit = async (promptText: string) => {
    setStatus("processing");
    setErrorMessage("");

    try {
      const res = await fetch(`${backendUrl}/api/v1/process-text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: promptText, session_id: sessionId }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();
      setCurrentRun(data);
      setStatus(data.audio_url ? "playing" : "idle");
      soundSynth.playSuccessBeep();
      fetchHistory();
    } catch (err: any) {
      console.error("Text command failed:", err);
      setErrorMessage(err.message || "Failed to communicate with ultron backend.");
      setStatus("error");
      soundSynth.playErrorAlert();
    }
  };

  // Process Audio Blob via Backend Endpoint
  const processAudio = async (audioBlob: Blob) => {
    setStatus("processing");
    setErrorMessage("");

    try {
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);

      reader.onloadend = async () => {
        const base64Audio = (reader.result as string).split(",")[1];

        const res = await fetch(`${backendUrl}/api/v1/process-audio`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ audio_base64: base64Audio, session_id: sessionId }),
        });

        if (!res.ok) {
          throw new Error(`Pipeline returned status ${res.status}`);
        }

        const data = await res.json();
        setCurrentRun(data);
        setStatus(data.audio_url ? "playing" : "idle");
        soundSynth.playSuccessBeep();
        fetchHistory();
      };
    } catch (err: any) {
      console.error("Audio processing failed:", err);
      setErrorMessage(err.message || "Failed to process audio pipeline.");
      setStatus("error");
      soundSynth.playErrorAlert();
    }
  };

  return (
    <div className="relative min-h-screen w-full flex flex-col justify-between overflow-x-hidden text-slate-100 font-sans">
      {/* Sci-Fi Canvas Background Grid */}
      <SciFiBackground status={status} />

      {/* Top Telemetry Navigation Header */}
      <HudHeader
        status={status}
        backendUrl={backendUrl}
        sessionId={sessionId}
        onOpenSettings={() => setShowSettings(true)}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        isSidebarOpen={isSidebarOpen}
        soundEnabled={soundEnabled}
        onToggleSound={handleToggleSound}
      />

      {/* Main Center Content Viewport */}
      <main className="relative z-10 flex-1 max-w-6xl w-full mx-auto px-4 py-3 flex flex-col items-center justify-between">
        {/* Mind-Blowing Central HUD Pulsar Core */}
        <PulsarCore
          status={status}
          recordingTime={recordingTime}
          micVolume={micVolume}
          onStartRecording={startRecording}
          onStopRecording={stopRecording}
          wakeWordStatus={wakeWordStatus}
          wakeWordTranscript={wakeWordTranscript}
          errorMessage={errorMessage}
        />

        {/* 7-Stage State Machine Pipeline Telemetry Bar */}
        <PipelineTracker
          currentRun={currentRun}
          detailedRun={detailedRun}
          isProcessing={status === "processing"}
        />

        {/* Futuristic Command Input Console */}
        <ConsoleInput
          input={inputCommand}
          setInput={setInputCommand}
          onSubmit={handleTextSubmit}
          isProcessing={status === "processing"}
          wakeWordEnabled={wakeWordEnabled}
          onToggleWakeWord={() => {
            const next = !wakeWordEnabled;
            setWakeWordEnabled(next);
            localStorage.setItem("ultron_wake_word_enabled", next.toString());
          }}
        />

        {/* Tactical Dashboard Widgets (Response, Weather, Calendar, Tasks, System) */}
        <UltronWidgets
          currentRun={currentRun}
          backendUrl={backendUrl}
          onSendPrompt={handleTextSubmit}
        />
      </main>

      {/* Telemetry Sidebar Drawer */}
      <TelemetrySidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        history={history}
        onSelectRun={(run) => {
          setDetailedRun(run);
          soundSynth.playClick();
        }}
        onFetchHistory={fetchHistory}
      />

      {/* System Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        backendUrl={backendUrl}
        setBackendUrl={setBackendUrl}
        sessionId={sessionId}
        setSessionId={setSessionId}
        wakeWordEnabled={wakeWordEnabled}
        setWakeWordEnabled={setWakeWordEnabled}
      />
    </div>
  );
}
