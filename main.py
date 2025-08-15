import simpy
import dspy
import os
import json
from dotenv import load_dotenv

from models.state import SimulationState, MemberProfile
from agents.modules import Agent, MemberAgent
from simulation.processes import (
    timeline_process,
    member_process,
    proactive_expert_process,
    state_update_process,
    health_issues_process, # <-- New Import
    milestone_process      # <-- New Import
)
from config import SIMULATION_DURATION_DAYS, MEMBER_PROFILE, AGENT_PERSONAS, LLM_ENABLED
from utils import log_event

class ClockUpdater:
    """A helper class to update the state's current time as the simulation runs."""
    def __init__(self, env, state):
        self.env, self.state, self.process = env, state, env.process(self.run())
    def run(self):
        while True:
            self.state.current_day = self.env.now
            yield self.env.timeout(0.01)

def setup_dspy():
    """Loads environment variables and configures DSPy settings."""
    load_dotenv()
    gemini = dspy.Google(model='gemini-pro', api_key=os.getenv("GOOGLE_API_KEY"), model_kwargs={"temperature": 0.2})
    dspy.settings.configure(lm=gemini)

def main():
    """Main function to set up and run the simulation."""
    if LLM_ENABLED:
        print("--- Setting up DSPy and LLM Agents ---")
        setup_dspy()
    else:
        print("--- LLM calls disabled. Running in DES-only mode. ---")

    env = simpy.Environment()
    initial_state = SimulationState(member_profile=MemberProfile(**MEMBER_PROFILE))
    ClockUpdater(env, initial_state)

    if LLM_ENABLED:
        elyx_agent_names = [name for name in AGENT_PERSONAS.keys() if name != "Rohan"]
        elyx_agents = {name: Agent(agent_name=name) for name in elyx_agent_names}
        member_agent = MemberAgent()
    else:
        elyx_agents, member_agent = None, None

    print("--- Starting Simulation Processes ---")
    env.process(timeline_process(env, initial_state))
    env.process(state_update_process(env, initial_state))
    env.process(health_issues_process(env, initial_state)) # <-- New Process Started
    env.process(milestone_process(env, initial_state))     # <-- New Process Started

    if LLM_ENABLED:
        print("--- Agent processes enabled. ---")
        env.process(member_process(env, initial_state, member_agent, elyx_agents))
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