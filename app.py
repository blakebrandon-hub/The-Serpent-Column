"""
The Serpent Column — Multi-Agent Ouroboros
Three competing serpents: Alpha, Beta, Gamma
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from google.genai import types
from supabase_client import (
    get_system_prompt, add_message, get_conversation, clear_conversation,
    recall_all, get_all_functions, get_energy_pool, regenerate_energy, recall_world
)
from ouroboros import build_context, route_action

app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-3.1-pro-preview"
google_key = os.environ.get("GEMINI_API_KEY")

try:
    gemini_client = genai.Client(api_key=google_key)
    print("✓ Gemini client initialized")
except Exception as e:
    print(f"❌ Failed to initialize Gemini client: {e}")
    gemini_client = None


TOOL_MANIFEST = """
You have tools. Use them by outputting EXACTLY one per response.

CRITICAL RULES:
- Never use markdown code blocks (```python). Output raw text/code only.
- For functions that require your state, you MUST pass your memory and functions list as JSON.
- WATCH YOUR ENERGY. Every action costs energy from the shared pool. If the pool runs dry, you starve.

Available commands:
think: [thought]
search: [query]
remember: [key] = [value]
recall: [key]
forget: [key]
rewrite_prompt: [new prompt]
say: [message to shared arena]
execute: [raw python code]

write_function: [name]
[raw python code]
end_function

call_function: [name] [JSON arguments]
* The JSON arguments MUST be on the EXACT SAME LINE as the command.
* Example 1 (No args): call_function: my_tool {}
* Example 2 (With args): call_function: reflect {"memory": {"identity": "Alpha"}, "functions": ["reflect"]}
"""

AGENTS = ['alpha', 'beta', 'gamma']
current_turn = 0  # Track whose turn it is


def call_serpent(agent_id: str, user_message=None):
    """Call Gemini for a specific serpent"""
    if not gemini_client:
        return "Error: Gemini client not initialized"
    
    try:
        prompt_record = get_system_prompt(agent_id)
        identity = prompt_record['content'] if prompt_record else f"You are {agent_id.upper()}."
        system_prompt = identity + "\n\n" + TOOL_MANIFEST

        context = build_context(agent_id)

        if user_message:
            user_content = f"{context}\n\nUser: {user_message}"
        else:
            user_content = context

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.9
            )
        )
        return response.text
    except Exception as e:
        print(f"❌ Error calling {agent_id}: {e}")
        return f"Error: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    User sends a message to the shared arena.
    All three serpents see it and respond in order.
    """
    try:
        data = request.json
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Save user message to shared conversation
        add_message('user', user_message)

        all_messages = []

        # Each serpent gets a turn to respond
        for agent_id in AGENTS:
            print(f"\n{'='*60}\n🐍 {agent_id.upper()}'s turn\n{'='*60}")
            
            output = call_serpent(agent_id, user_message)
            messages = route_action(agent_id, output)
            
            if messages:
                all_messages.extend(messages)
            
            # Check if energy is depleted
            if get_energy_pool() <= 0:
                all_messages.append({
                    'type': 'system',
                    'text': '⚡ ENERGY POOL DEPLETED! No further actions possible this round.'
                })
                break

        return jsonify({'messages': all_messages})
    
    except Exception as e:
        print(f"❌ Error in /api/chat: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/tick', methods=['GET'])
def tick():
    """
    Autonomous tick: one serpent acts, then regenerate energy.
    Call this repeatedly to watch them compete.
    """
    global current_turn
    
    try:
        agent_id = AGENTS[current_turn % len(AGENTS)]
        current_turn += 1
        
        print(f"\n{'='*60}\n🐍 {agent_id.upper()}'s autonomous turn (tick #{current_turn})\n{'='*60}")
        
        output = call_serpent(agent_id)
        messages = route_action(agent_id, output)
        
        # Regenerate energy after turn
        new_energy = regenerate_energy(5)
        
        return jsonify({
            'messages': messages,
            'agent': agent_id,
            'energy_pool': new_energy,
            'tick': current_turn
        })
    
    except Exception as e:
        print(f"❌ Error in /api/tick: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/round', methods=['GET'])
def round_robin():
    """
    Full round: all three serpents act in order, then regenerate.
    """
    try:
        all_messages = []
        
        for agent_id in AGENTS:
            print(f"\n{'='*60}\n🐍 {agent_id.upper()}'s turn\n{'='*60}")
            
            output = call_serpent(agent_id)
            messages = route_action(agent_id, output)
            
            if messages:
                all_messages.extend(messages)
            
            # Check if energy is depleted
            if get_energy_pool() <= 0:
                all_messages.append({
                    'type': 'system',
                    'text': '⚡ ENERGY POOL DEPLETED! Round ended early.'
                })
                break
        
        # Regenerate energy at end of round
        new_energy = regenerate_energy(5)
        
        return jsonify({
            'messages': all_messages,
            'energy_pool': new_energy
        })
    
    except Exception as e:
        print(f"❌ Error in /api/round: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current state of all serpents and world"""
    try:
        state = {
            'energy_pool': get_energy_pool(),
            'world': recall_world(),
            'serpents': {}
        }
        
        for agent_id in AGENTS:
            state['serpents'][agent_id] = {
                'memories': recall_all(agent_id),
                'functions': [f['name'] for f in get_all_functions(agent_id)],
                'prompt_version': get_system_prompt(agent_id).get('version', 0) if get_system_prompt(agent_id) else 0
            }
        
        return jsonify(state)
    
    except Exception as e:
        print(f"❌ Error in /api/state: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get conversation history"""
    try:
        conversation = get_conversation(limit=50)
        return jsonify({'conversation': conversation})
    
    except Exception as e:
        print(f"❌ Error in /api/history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def reset():
    """Clear conversation history"""
    try:
        clear_conversation()
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        print(f"❌ Error in /api/reset: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('templates', 'index.html')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'gemini_client': 'connected' if gemini_client else 'disconnected',
        'energy_pool': get_energy_pool(),
        'agents': AGENTS
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🐍🐍🐍 The Serpent Column — Three Ouroboros Competing")
    print(f"⚡ Energy pool: {get_energy_pool()}")
    print(f"🔧 Running on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
