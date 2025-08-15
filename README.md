# Med Data Generation

A discrete-event simulation that models a personalized medical support program for a client. The project combines deterministic processes with stochastic events and large language model (LLM) agents to produce synthetic conversations, interventions and health data.

## Features

- **SimPy-based timeline** for scheduling onboarding, interventions and follow-up events.
- **LLM-driven agents** that respond with role‑specific personas and generate member questions.
- **Semantic router** to choose the appropriate expert for each member question.
- **Configurable stochastic processes** for plan adherence, travel and health issues.
- **Structured event logging** saved to `simulation_log.json` for downstream analysis.

## Repository Structure

| Path | Purpose |
| --- | --- |
| `config.py` | Simulation parameters, agent personas and LLM toggle. |
| `agents/` | DSPy modules implementing expert, member and routing agents. |
| `models/` | Pydantic models describing the simulation state. |
| `simulation/` | Processes that drive the timeline and probabilistic events. |
| `utils.py` | Logging helpers and context distillation for the LLM. |
| `main.py` | Entry point that wires everything together and runs the simulation. |

## Getting Started

1. **Install Dependencies**

   ```bash
   pip install -e .
   ```

2. **Set Environment Variables**

   The project uses Google Gemini through DSPy. Export your API key before running the simulation:

   ```bash
   export GOOGLE_API_KEY="your-key"
   ```

3. **Run the Simulation**

   ```bash
   python main.py
   ```

   Events are printed to the console and persisted to `simulation_log.json`.

## Configuration

Edit `config.py` to customize the run:

- `LLM_ENABLED` toggles between a pure SimPy simulation and one that calls the LLM agents.
- `SIMULATION_DURATION_DAYS` controls how long the environment runs.
- `AVG_DAYS_PER_MEMBER_QUESTION`, `PLAN_ADHERENCE_PROBABILITY` and other constants tune stochastic behavior.
- `MEMBER_PROFILE` and `AGENT_PERSONAS` define the personalities used by the agents.

## Notes

The codebase is still evolving; some modules such as event handlers are stubs. Contributions and issue reports are welcome.

