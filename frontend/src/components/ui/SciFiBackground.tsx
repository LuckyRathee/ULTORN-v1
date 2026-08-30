"use client";

import React, { useEffect, useRef } from "react";

interface SciFiBackgroundProps {
  status?: "idle" | "recording" | "processing" | "playing" | "error";
}

export const SciFiBackground: React.FC<SciFiBackgroundProps> = ({ status = "idle" }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener("resize", handleResize);

    // Particle nodes for HUD mesh network
    const particleCount = 45;
    const particles = Array.from({ length: particleCount }).map(() => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      radius: Math.random() * 1.5 + 0.5,
      alpha: Math.random() * 0.5 + 0.2,
    }));

    let laserY = 0;
    const laserSpeed = 1.2;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Render Subtle Grid Lines
      const gridSize = 40;
      ctx.strokeStyle = "rgba(6, 182, 212, 0.03)";
      ctx.lineWidth = 1;

      ctx.beginPath();
      for (let x = 0; x < width; x += gridSize) {
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
      }
      ctx.stroke();

      // Render Scanning Laser Line
      laserY += laserSpeed;
      if (laserY > height) laserY = 0;

      const laserGrad = ctx.createLinearGradient(0, laserY - 15, 0, laserY + 15);
      laserGrad.addColorStop(0, "rgba(6, 182, 212, 0)");
      laserGrad.addColorStop(
        0.5,
        status === "recording"
          ? "rgba(244, 63, 94, 0.12)"
          : status === "processing"
          ? "rgba(245, 158, 11, 0.12)"
          : "rgba(6, 182, 212, 0.08)"
      );
      laserGrad.addColorStop(1, "rgba(6, 182, 212, 0)");

      ctx.fillStyle = laserGrad;
      ctx.fillRect(0, laserY - 15, width, 30);

      // Draw Particle Mesh
      particles.forEach((p, idx) => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.fillStyle =
          status === "recording"
            ? `rgba(244, 63, 94, ${p.alpha})`
            : status === "processing"
            ? `rgba(245, 158, 11, ${p.alpha})`
            : `rgba(6, 182, 212, ${p.alpha})`;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();

        // Connect near particles
        for (let j = idx + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 110) {
            ctx.strokeStyle =
              status === "recording"
                ? `rgba(244, 63, 94, ${0.15 * (1 - dist / 110)})`
                : status === "processing"
                ? `rgba(245, 158, 11, ${0.15 * (1 - dist / 110)})`
                : `rgba(6, 182, 212, ${0.08 * (1 - dist / 110)})`;
            ctx.lineWidth = 0.5;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [status]);

  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {/* Dynamic Ambient Background Glow */}
      <div
        className={`absolute inset-0 transition-all duration-700 ${
          status === "recording"
            ? "bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-rose-950/20 via-slate-950/80 to-[#030712]"
            : status === "processing"
            ? "bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-amber-950/20 via-slate-950/80 to-[#030712]"
            : status === "error"
            ? "bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-red-950/30 via-slate-950/80 to-[#030712]"
            : "bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-cyan-950/20 via-slate-950/80 to-[#030712]"
        }`}
      />

      {/* HTML5 Canvas overlay */}
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full opacity-70" />

      {/* Sci-Fi Corner HUD Bracket Markers */}
      <div className="absolute top-4 left-4 text-[10px] font-mono text-cyan-500/40 select-none tracking-widest">
        ┌ TOP_LEFT // SYS.RESERVED
      </div>
      <div className="absolute top-4 right-4 text-[10px] font-mono text-cyan-500/40 select-none tracking-widest text-right">
        TOP_RIGHT // HUD.V2.0 ┐
      </div>
      <div className="absolute bottom-4 left-4 text-[10px] font-mono text-cyan-500/40 select-none tracking-widest">
        └ BOT_LEFT // PIPELINE.LIVE
      </div>
      <div className="absolute bottom-4 right-4 text-[10px] font-mono text-cyan-500/40 select-none tracking-widest text-right">
        BOT_RIGHT // SUPABASE.CONNECTED ┘
      </div>
    </div>
  );
};
