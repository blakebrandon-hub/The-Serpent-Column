"""
Ouroboros — Supabase Client (Multi-Agent Edition)
Memory, system prompt versioning, function storage, conversation history
Now with agent_id partitioning and energy tracking
"""

import os
from datetime import datetime
from supabase import create_client, Client

# Use environment variables in production
SUPABASE_URL = os.environ.get("OUROBOROS_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("OUROBOROS_SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# ENERGY MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

ENERGY_COSTS = {
    'think': 1,
    'say': 2,
    'search': 10,
    'execute': 5,
    'write_function': 15,
    'call_function': 3,
    'rewrite_prompt': 20,
    'remember': 2,
    'recall': 1,
    'forget': 2,
}

def get_energy_pool() -> int:
    """Get current energy pool from world memory"""
    try:
        result = (supabase.table('memory')
                  .select('value')
                  .eq('agent_id', 'world')
                  .eq('key', 'energy_pool')
                  .execute())
        if result.data:
            return int(result.data[0]['value'])
        return 0
    except Exception as e:
        print(f"❌ Error getting energy pool: {e}")
        return 0


def deduct_energy(cost: int) -> bool:
    """
    Deduct energy from the world pool.
    Returns True if successful, False if insufficient energy.
    """
    try:
        current = get_energy_pool()
        if current < cost:
            print(f"⚡ INSUFFICIENT ENERGY: need {cost}, have {current}")
            return False
        
        new_value = current - cost
        supabase.table('memory').update({
            'value': str(new_value)
        }).eq('agent_id', 'world').eq('key', 'energy_pool').execute()
        
        print(f"⚡ Energy: {current} → {new_value} (-{cost})")
        return True
    except Exception as e:
        print(f"❌ Error deducting energy: {e}")
        return False


def regenerate_energy(amount: int = 5) -> int:
    """Add energy to the pool (called between rounds)"""
    try:
        current = get_energy_pool()
        new_value = current + amount
        
        supabase.table('memory').update({
            'value': str(new_value)
        }).eq('agent_id', 'world').eq('key', 'energy_pool').execute()
        
        print(f"⚡ Energy regenerated: {current} → {new_value} (+{amount})")
        return new_value
    except Exception as e:
        print(f"❌ Error regenerating energy: {e}")
        return current


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

def get_system_prompt(agent_id: str) -> dict:
    """Get the latest system prompt for an agent"""
    try:
        result = (supabase.table('system_prompt')
                  .select('*')
                  .eq('agent_id', agent_id)
                  .order('version', desc=True)
                  .limit(1)
                  .execute())
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error getting system prompt for {agent_id}: {e}")
        return None


def rewrite_system_prompt(agent_id: str, new_content: str) -> dict:
    """Save a new version of the system prompt for an agent"""
    try:
        current = get_system_prompt(agent_id)
        new_version = (current['version'] + 1) if current else 1

        result = supabase.table('system_prompt').insert({
            'agent_id': agent_id,
            'version': new_version,
            'content': new_content
        }).execute()

        print(f"📜 [{agent_id.upper()}] System prompt rewritten → version {new_version}")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error rewriting system prompt for {agent_id}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MEMORY
# ─────────────────────────────────────────────────────────────────────────────

def remember(agent_id: str, key: str, value: str) -> dict:
    """Store or update a memory for an agent"""
    try:
        existing = (supabase.table('memory')
                    .select('*')
                    .eq('agent_id', agent_id)
                    .eq('key', key)
                    .execute())

        if existing.data:
            result = (supabase.table('memory')
                      .update({'value': value})
                      .eq('agent_id', agent_id)
                      .eq('key', key)
                      .execute())
        else:
            result = supabase.table('memory').insert({
                'agent_id': agent_id,
                'key': key,
                'value': value
            }).execute()

        print(f"🧠 [{agent_id.upper()}] Memory: {key} = {value[:60]}...")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error storing memory for {agent_id}: {e}")
        return None


def recall(agent_id: str, key: str) -> str:
    """Retrieve a memory by key for an agent"""
    try:
        result = (supabase.table('memory')
                  .select('value')
                  .eq('agent_id', agent_id)
                  .eq('key', key)
                  .execute())
        if result.data:
            return result.data[0]['value']
        return None
    except Exception as e:
        print(f"❌ Error recalling memory for {agent_id}: {e}")
        return None


def recall_all(agent_id: str) -> dict:
    """Get all memories for an agent as a key/value dict"""
    try:
        result = (supabase.table('memory')
                  .select('*')
                  .eq('agent_id', agent_id)
                  .execute())
        return {row['key']: row['value'] for row in result.data}
    except Exception as e:
        print(f"❌ Error recalling all memories for {agent_id}: {e}")
        return {}


def recall_world() -> dict:
    """Get all world-level memories"""
    return recall_all('world')


def forget(agent_id: str, key: str) -> bool:
    """Delete a memory for an agent"""
    try:
        supabase.table('memory').delete().eq('agent_id', agent_id).eq('key', key).execute()
        print(f"🧠 [{agent_id.upper()}] Memory deleted: {key}")
        return True
    except Exception as e:
        print(f"❌ Error deleting memory for {agent_id}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def save_function(agent_id: str, name: str, code: str, description: str = None) -> dict:
    """Save a function for an agent"""
    try:
        existing = (supabase.table('functions')
                    .select('*')
                    .eq('agent_id', agent_id)
                    .eq('name', name)
                    .execute())

        if existing.data:
            result = (supabase.table('functions')
                      .update({'code': code, 'description': description})
                      .eq('agent_id', agent_id)
                      .eq('name', name)
                      .execute())
        else:
            result = supabase.table('functions').insert({
                'agent_id': agent_id,
                'name': name,
                'code': code,
                'description': description
            }).execute()

        print(f"⚙️  [{agent_id.upper()}] Function saved: {name}")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error saving function for {agent_id}: {e}")
        return None


def get_function(agent_id: str, name: str) -> dict:
    """Get a function by name for an agent"""
    try:
        result = (supabase.table('functions')
                  .select('*')
                  .eq('agent_id', agent_id)
                  .eq('name', name)
                  .execute())
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error getting function for {agent_id}: {e}")
        return None


def get_all_functions(agent_id: str) -> list:
    """Get all saved functions for an agent"""
    try:
        result = (supabase.table('functions')
                  .select('*')
                  .eq('agent_id', agent_id)
                  .order('created_at')
                  .execute())
        return result.data
    except Exception as e:
        print(f"❌ Error getting all functions for {agent_id}: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSATION
# ─────────────────────────────────────────────────────────────────────────────

def add_message(role: str, content: str) -> dict:
    """Add a message to conversation history"""
    try:
        result = supabase.table('conversation').insert({
            'role': role,
            'content': content
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error adding message: {e}")
        return None


def get_conversation(limit: int = 20) -> list:
    """Get recent conversation history"""
    try:
        result = (supabase.table('conversation')
                  .select('*')
                  .order('created_at', desc=True)
                  .limit(limit)
                  .execute())
        entries = result.data
        entries.reverse()
        return entries
    except Exception as e:
        print(f"❌ Error getting conversation: {e}")
        return []


def clear_conversation() -> bool:
    """Clear all conversation history"""
    try:
        supabase.table('conversation').delete().gte('created_at', '1970-01-01').execute()
        print(f"💬 Conversation cleared")
        return True
    except Exception as e:
        print(f"❌ Error clearing conversation: {e}")
        return False
