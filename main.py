import simpy
import dspy
import os
import json
from dotenv import load_dotenv

from models.state import SimulationState, MemberProfile
# Import the new Router module
from agents.modules import Agent, MemberAgent, Router
from simulation.processes import (
    timeline_process, member_process, proactive_expert_process,
    state_update_process, health_issues_process, milestone_process
)
from config import (
    SIMULATION_DURATION_DAYS,
    MEMBER_PROFILE,
    AGENT_PERSONAS,
    LLM_ENABLED,
    LLM_MODEL,
    LLM_API_BASE,
)
from utils import log_event

class ClockUpdater:
    def __init__(self, env, state):
        self.env, self.state, self.process = env, state, env.process(self.run())
    def run(self):
        while True:
            self.state.current_day = self.env.now
            yield self.env.timeout(0.01)

def setup_dspy():
    """Configure DSPy to use the locally hosted LM Studio server."""
    load_dotenv()
    lm = dspy.OpenAI(
        model=LLM_MODEL,
        api_base=LLM_API_BASE,
        api_key=os.getenv("OPENAI_API_KEY", "lm-studio"),
    )
    dspy.configure(lm=lm)

def main():
    if LLM_ENABLED:
        print("--- Setting up DSPy and LLM Agents ---")
        setup_dspy()
    else:
        print("--- LLM calls disabled. Running in DES-only mode. ---")

    env = simpy.Environment()
    initial_state = SimulationState(member_profile=MemberProfile(**MEMBER_PROFILE))
    ClockUpdater(env, initial_state)

    # Initialize agents and the new router
    if LLM_ENABLED:
        elyx_agent_names = [name for name in AGENT_PERSONAS.keys() if name != "Rohan"]
        elyx_agents = {name: Agent(agent_name=name) for name in elyx_agent_names}
        member_agent = MemberAgent()
        # Create an instance of the router, excluding the default/logistics agent (Ruby)
        # so it focuses on routing to specialists.
        specialist_names = [name for name in elyx_agent_names if name != "Ruby"]
        router = Router(agent_names=specialist_names)
    else:
        elyx_agents, member_agent, router = None, None, None

    print("--- Starting Simulation Processes ---")
    env.process(timeline_process(env, initial_state))
    env.process(state_update_process(env, initial_state))
    env.process(health_issues_process(env, initial_state))
    env.process(milestone_process(env, initial_state))

    if LLM_ENABLED:
        print("--- Agent processes enabled with Semantic Routing. ---")
        # Pass the router into the member process
        env.process(member_process(env, initial_state, member_agent, elyx_agents, router))
        env.process(proactive_expert_process(env, initial_state, elyx_agents))

    log_event(initial_state, "SIM_START", "SIM_CORE", {"message": "Simulation starting."})
    print("\n--- Running Simulation ---")
    env.run(until=SIMULATION_DURATION_DAYS)
    print("\n--- Simulation Complete ---")
    log_event(initial_state, "SIM_END", "SIM_CORE", {"message": f"Simulation ended at day {env.now:.2f}."})

    output_filename = "simulation_log.json"
    with open(output_filename, 'w') as f:
        json.dump(initial_state.event_log, f, indent=2)

    print(f"\nFull simulation log saved to {output_filename}")

if __name__ == "__main__":
    main()
