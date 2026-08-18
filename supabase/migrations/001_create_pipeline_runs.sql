-- Migration: Create pipeline_runs table for Jarvis 2.0
-- Run this in Supabase SQL Editor

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create pipeline_runs table
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL,
    user_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'done', 'failed')),
    stages JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_latency_ms INTEGER NOT NULL DEFAULT 0
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_session_id ON pipeline_runs(session_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_user_id ON pipeline_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created_at ON pipeline_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);

-- Enable Row Level Security (RLS)
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service role to do everything (for backend)
CREATE POLICY "Service role full access" ON pipeline_runs
    FOR ALL
    USING (auth.role() = 'service_role');

-- Policy: Users can read their own runs (if using user auth)
CREATE POLICY "Users can read own runs" ON pipeline_runs
    FOR SELECT
    USING (auth.uid()::text = user_id);

-- Policy: Users can insert their own runs
CREATE POLICY "Users can insert own runs" ON pipeline_runs
    FOR INSERT
    WITH CHECK (auth.uid()::text = user_id);

-- Grant permissions
GRANT ALL ON pipeline_runs TO service_role;
GRANT SELECT, INSERT ON pipeline_runs TO authenticated;