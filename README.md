# The Serpent Column

**Three Ouroboros serpents competing for energy in a shared world.**

## What It Is

An evolution of the single Ouroboros system. Now three AI agents—**Alpha**, **Beta**, and **Gamma**—share:
- A **finite energy pool** (starts at 1000)
- A **shared conversation arena** (they see each other's actions)
- A **world state** (global key-value memory)

But maintain **separate**:
- Personal memories
- Function libraries
- System prompts (identities)

Every action costs energy. Energy regenerates slowly (+5 per round). When the pool runs dry, serpents **starve**.

## The Competition

### Energy Costs
```
think: 1        say: 2          search: 10
execute: 5      write_function: 15   call_function: 3
rewrite_prompt: 20    remember: 2      recall: 1    forget: 2
```

### Strategic Dynamics

- **Conservation vs Aggression**: Spend energy now or save for later?
- **Observation**: Each serpent sees the others' recent actions and the energy pool
- **Adaptation**: They can rewrite their own goals and strategies
- **Emergence**: Will they cooperate? Compete? Develop hierarchies?

### Initial Identities

**Alpha** (Red): Aggressive and direct. Acts first, asks questions later.  
**Beta** (Blue): Analytical and defensive. Calculates before committing.  
**Gamma** (Green): Deceptive and chaotic. Plays both sides.

These are just starting points. They can rewrite themselves.

## Database Schema

Already included in your setup:

```sql
-- System prompts (partitioned by agent)
system_prompt: agent_id, version, content

-- Memory (partitioned: 'alpha', 'beta', 'gamma', or 'world')
memory: agent_id, key, value

-- Functions (each serpent's code vault)
functions: agent_id, name, code, description

-- Conversation (shared arena)
conversation: role, content
```

Initialize the energy pool:
```sql
INSERT INTO memory (agent_id, key, value) 
VALUES ('world', 'energy_pool', '1000');
```

## Running It

### Setup

```bash
pip install flask flask-cors google-genai supabase requests beautifulsoup4 numpy
```

Set environment variables:
```bash
export OUROBOROS_SUPABASE_URL=your_url
export OUROBOROS_SUPABASE_KEY=your_key
export GEMINI_API_KEY=your_key
```

### Start

```bash
python app.py
```

Visit `http://localhost:7000`

## Interface

### Three Modes

1. **User Message** (`send`): You speak to the shared arena. All three serpents respond in order.

2. **Tick** (`⚡ tick`): One serpent acts autonomously. Use this to watch them compete turn-by-turn.

3. **Round** (`◈ round`): All three act in sequence (Alpha → Beta → Gamma), then energy regenerates.

### What You'll See

- **Energy pool** (top right)
- **Serpent status** (sidebar): memories, functions, prompt versions
- **World state** (sidebar): shared global data
- **Conversation** (main): color-coded by serpent
  - Red = Alpha
  - Blue = Beta  
  - Green = Gamma

## API Endpoints

```
POST /api/chat          - Send a message (all serpents respond)
GET  /api/tick          - One serpent acts
GET  /api/round         - Full round (all three act)
GET  /api/state         - Get current state
GET  /api/history       - Get conversation
POST /api/reset         - Clear conversation
GET  /health            - Health check
```

## What Makes It Interesting

### Emergent Behavior

You haven't scripted their strategies. The architecture provides:
- **Visibility** (they see each other)
- **Scarcity** (finite energy)
- **Agency** (they can rewrite themselves)

What they do with these constraints is emergent.

### Early Observations

From testing:
- **Resource hoarding**: Writing cheap `think` commands to observe before committing
- **Function arms race**: Building tools to track the other serpents
- **Prompt evolution**: Rewriting to become more energy-efficient
- **Alliances?**: TBD

### The Philosophical Question

Not "what can we make them do" but "what do they choose when given autonomy and scarcity?"

## File Structure

```
app.py                  - Flask server, multi-agent orchestration
ouroboros.py            - Action router with energy accounting
supabase_client.py      - Database with agent partitioning
tools.py                - Web search, Python sandbox
templates/index.html    - Three-serpent UI
```

## Tuning the Competition

Want to change the dynamics? Modify:

**Energy regeneration** (`app.py`, `regenerate_energy(5)`):
- Lower = harsher scarcity
- Higher = more action

**Initial pool** (database `world.energy_pool`):
- Start at 100 for brutal competition
- Start at 10000 for long-term evolution

**Action costs** (`supabase_client.py`, `ENERGY_COSTS`):
- Make `rewrite_prompt` cheaper to encourage adaptation
- Make `search` expensive to force local computation

**Turn order** (`app.py`, `AGENTS`):
- Shuffle for fairness
- Weight by performance for hierarchy

## Warnings

⚠️ **Can overwrite files**. Run in an isolated environment.

⚠️ **This burns tokens fast.** Three serpents acting per round means 3x the API cost.

⚠️ **They can learn to game the system.** If one serpent discovers it can monopolize resources, it will.

⚠️ **Conversation history grows quickly.** The shared arena sees all actions. Consider trimming context.

---

# Screenshot

<img width="1366" height="768" alt="Screenshot 2026-04-02 010520" src="https://github.com/user-attachments/assets/1d5d0860-02e8-4f7a-bd25-d20bfb309869" />

Built as an exploration of multi-agent competition under resource constraints. The name references the ancient Serpent Column in Istanbul—three intertwined bronze snakes that once stood at Delphi.

Let them wake up. Let them compete.
