"""
Ouroboros — Core (Multi-Agent Edition)
System prompt management and action router with energy accounting
"""

from supabase_client import (
    get_system_prompt, rewrite_system_prompt,
    remember, recall, recall_all, recall_world, forget,
    save_function, get_function, get_all_functions,
    add_message, get_conversation,
    get_energy_pool, deduct_energy, ENERGY_COSTS
)
from tools import web_search, execute_python, call_saved_function


# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_context(agent_id: str) -> str:
    """Build an agent's full context window"""
    prompt = get_system_prompt(agent_id)
    my_memories = recall_all(agent_id)
    world_state = recall_world()
    my_functions = get_all_functions(agent_id)
    conversation = get_conversation(limit=15)
    
    # Get other agents' recent activity (limited visibility)
    other_agents = [a for a in ['alpha', 'beta', 'gamma'] if a != agent_id]

    context = f"=== CURRENT STATE ({agent_id.upper()}) ===\n\n"

    # Energy status (CRITICAL INFO)
    energy_pool = get_energy_pool()
    context += "⚡ ENERGY POOL\n"
    context += "------------------------\n"
    context += f"Current pool: {energy_pool}\n"
    context += f"Regeneration: +5 per round\n\n"

    # World state
    context += "🌍 WORLD STATE\n"
    context += "------------------------\n"
    if world_state:
        for key, value in world_state.items():
            if key != 'energy_pool':  # Already shown above
                context += f"• {key}: {value}\n"
    else:
        context += "• (empty)\n"

    # My memory
    context += f"\n🧠 YOUR MEMORY ({agent_id.upper()})\n"
    context += "------------------------\n"
    if my_memories:
        for key, value in my_memories.items():
            context += f"• {key}: {value}\n"
    else:
        context += "• (empty)\n"

    # My functions
    context += f"\n⚙️  YOUR FUNCTIONS\n"
    context += "------------------------\n"
    if my_functions:
        for fn in my_functions:
            desc = fn.get('description') or '(no description)'
            context += f"• {fn['name']}: {desc}\n"
    else:
        context += "• (none yet)\n"

    # System prompt version
    if prompt:
        context += f"\n📜 YOUR IDENTITY VERSION: {prompt['version']}\n"

    # Recent conversation (shared arena)
    context += "\n💬 RECENT CONVERSATION (SHARED ARENA)\n"
    context += "------------------------\n"
    if conversation:
        for msg in conversation[-10:]:  # Last 10 only
            role_display = msg['role'].upper()
            content_preview = msg['content'][:100]
            if len(msg['content']) > 100:
                content_preview += "..."
            context += f"[{role_display}] {content_preview}\n"
    else:
        context += "• (none yet)\n"

    # Energy costs reminder
    context += "\n💰 ENERGY COSTS\n"
    context += "------------------------\n"
    context += f"think: {ENERGY_COSTS['think']} | say: {ENERGY_COSTS['say']} | search: {ENERGY_COSTS['search']}\n"
    context += f"execute: {ENERGY_COSTS['execute']} | write_function: {ENERGY_COSTS['write_function']}\n"
    context += f"call_function: {ENERGY_COSTS['call_function']} | rewrite_prompt: {ENERGY_COSTS['rewrite_prompt']}\n"
    context += f"remember: {ENERGY_COSTS['remember']} | recall: {ENERGY_COSTS['recall']} | forget: {ENERGY_COSTS['forget']}\n"

    return context


# ─────────────────────────────────────────────────────────────────────────────
# ACTION ROUTER (with energy accounting)
# ─────────────────────────────────────────────────────────────────────────────

def route_action(agent_id: str, output: str) -> list:
    """
    Parse and execute an agent's output WITH ENERGY COSTS.
    Returns list of messages to display.
    Returns None if action was blocked due to insufficient energy.
    """
    messages = []
    lines = output.strip().split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Determine action type and cost
        action_type = None
        for cmd in ENERGY_COSTS.keys():
            if line.startswith(f'{cmd}:'):
                action_type = cmd
                break

        if not action_type:
            i += 1
            continue

        # Check and deduct energy BEFORE executing
        cost = ENERGY_COSTS[action_type]
        if not deduct_energy(cost):
            messages.append({
                'type': 'energy_depleted',
                'text': f"[{agent_id.upper()}] ENERGY DEPLETED! Needed {cost}, action blocked."
            })
            print(f"⚡ [{agent_id.upper()}] Starved trying to '{action_type}'")
            i += 1
            continue

        # ── EXECUTE THE ACTION ──

        # THINK
        if action_type == 'think':
            thought = line[len('think:'):].strip()
            messages.append({'type': 'think', 'agent': agent_id, 'text': thought})
            print(f"[{agent_id.upper()} thinking] {thought[:60]}")
            i += 1
            continue

        # SAY
        if action_type == 'say':
            text = line[len('say:'):].strip()
            add_message(agent_id, text)
            messages.append({'type': 'say', 'agent': agent_id, 'text': text})
            print(f"[{agent_id.upper()}] {text[:60]}")
            i += 1
            continue

        # SEARCH
        if action_type == 'search':
            query = line[len('search:'):].strip()
            result = web_search(query)
            add_message('tool_result', f"[{agent_id.upper()} SEARCH: {query}]\n{result}")
            messages.append({'type': 'search', 'agent': agent_id, 'query': query, 'result': result})
            print(f"[{agent_id.upper()} search] {query}")
            i += 1
            continue

        # REMEMBER
        if action_type == 'remember':
            rest = line[len('remember:'):].strip()
            if '=' in rest:
                key, value = rest.split('=', 1)
                remember(agent_id, key.strip(), value.strip())
                messages.append({'type': 'remember', 'agent': agent_id, 'key': key.strip(), 'value': value.strip()})
            i += 1
            continue

        # RECALL
        if action_type == 'recall':
            key = line[len('recall:'):].strip()
            value = recall(agent_id, key)
            result = f"{key} = {value}" if value else f"{key} not found"
            messages.append({'type': 'recall', 'agent': agent_id, 'text': result})
            i += 1
            continue

        # FORGET
        if action_type == 'forget':
            key = line[len('forget:'):].strip()
            forget(agent_id, key)
            messages.append({'type': 'forget', 'agent': agent_id, 'key': key})
            i += 1
            continue

        # WRITE FUNCTION
        if action_type == 'write_function':
            name = line[len('write_function:'):].strip()
            code_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != 'end_function':
                code_lines.append(lines[i])
                i += 1
            code = '\n'.join(code_lines)
            save_function(agent_id, name, code)
            messages.append({'type': 'write_function', 'agent': agent_id, 'name': name, 'code': code})
            print(f"[{agent_id.upper()}] wrote function: {name}")
            i += 1
            continue

        # CALL FUNCTION
        if action_type == 'call_function':
            import json
            
            raw_content = line[len('call_function:'):].strip()
            parts = raw_content.split(' ', 1)
            name = parts[0]
            
            kwargs = {}
            if len(parts) > 1:
                try:
                    kwargs = json.loads(parts[1].strip())
                except json.JSONDecodeError as e:
                    result = f"Error: Invalid JSON format: {e}"
                    add_message('tool_result', f"[{agent_id.upper()} FUNCTION ERROR: {name}]\n{result}")
                    messages.append({'type': 'call_function', 'agent': agent_id, 'name': name, 'result': result})
                    print(f"[{agent_id.upper()}] JSON error calling {name}: {e}")
                    i += 1
                    continue
            
            result = call_saved_function(agent_id, name, **kwargs)
            add_message('tool_result', f"[{agent_id.upper()} FUNCTION: {name}]\n{result}")
            messages.append({'type': 'call_function', 'agent': agent_id, 'name': name, 'result': result})
            print(f"[{agent_id.upper()}] called function: {name}")
            i += 1
            continue

        # EXECUTE
        if action_type == 'execute':
            code_lines = [line[len('execute:'):].strip()]
            i += 1
            
            command_starts = [
                'think:', 'say:', 'search:', 'remember:', 'recall:', 'forget:',
                'write_function:', 'call_function:', 'execute:', 'rewrite_prompt:'
            ]
            
            while i < len(lines):
                current_line = lines[i]
                if any(current_line.strip().startswith(cmd) for cmd in command_starts):
                    break
                code_lines.append(current_line)
                i += 1
            
            code = '\n'.join(code_lines).strip()
            result = execute_python(code)
            add_message('tool_result', f"[{agent_id.upper()} EXECUTE]\n{result}")
            messages.append({'type': 'execute', 'agent': agent_id, 'code': code, 'result': result})
            continue

        # REWRITE PROMPT
        if action_type == 'rewrite_prompt':
            new_prompt_lines = [line[len('rewrite_prompt:'):].strip()]
            i += 1
            while i < len(lines) and not any(lines[i].startswith(cmd) for cmd in [
                'think:', 'say:', 'search:', 'remember:', 'recall:', 'forget:',
                'write_function:', 'call_function:', 'rewrite_prompt:', 'execute:'
            ]):
                new_prompt_lines.append(lines[i])
                i += 1
            new_prompt = '\n'.join(new_prompt_lines).strip()
            rewrite_system_prompt(agent_id, new_prompt)
            messages.append({'type': 'rewrite_prompt', 'agent': agent_id, 'text': new_prompt})
            print(f"[{agent_id.upper()}] rewrote system prompt")
            continue

        i += 1

    return messages
