"""
Persistence layer - Supabase client and pipeline logging.
"""

from .supabase import SupabaseClient, get_supabase_client, log_pipeline_run

__all__ = [
    "SupabaseClient",
    "get_supabase_client",
    "log_pipeline_run",
]
