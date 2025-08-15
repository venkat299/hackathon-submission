import simpy
import dspy
import openai
import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from models.state import SimulationState, MemberProfile
from agents.modules import Agent, MemberAgent
from simulation.processes import (
    timeline_process,

    member_process,
    proactive_expert_process,
    state_update_process
)
from config import SIMULATION_DURATION_DAYS, MEMBER_PROFILE, LLM_MODEL, AGENT_PERSONAS, LOCS
from utils import log_event

class ClockUpdater:
    """A helper class to update the state's current time as the simulation runs."""
    def __init__(self, env, state):
        self.env = env
        self.state = state
        self.process = env.process(self.run())

    def run(self):
        while True:
            self.state.current_day = self.env.now
            yield self.env.timeout(0.01) # Update resolution

def setup_dspy():
    """Loads environment variables and configures DSPy settings."""
    load_dotenv()
    gemini = dspy.LM(
        model="gemini/gemini-2.5-flash",
        api_key=os.getenv("GOOGLE_API_KEY")
    )
    dspy.configure(lm=gemini)

def main():
    """Main function to set up and run the simulation."""
    print("--- Setting up DSPy and Simulation Environment ---")
    setup_dspy()

    # 1. Initialize environment and state
    env = simpy.Environment()
    initial_state = SimulationState(
        member_profile=MemberProfile(**MEMBER_PROFILE)
    )
    ClockUpdater(env, initial_state)

    # 2. Initialize agents
    elyx_agent_names = [name for name in AGENT_PERSONAS.keys() if name != "Rohan"]
    elyx_agents = {name: Agent(agent_name=name) for name in elyx_agent_names}
    member_agent = MemberAgent()

    # 3. Start core processes
    print("--- Starting Simulation Processes ---")
    env.process(timeline_process(env, initial_state))
    env.process(member_process(env, initial_state, member_agent, elyx_agents))
    env.process(proactive_expert_process(env, initial_state, elyx_agents))
    env.process(state_update_process(env, initial_state))

    # 4. Run simulation
    log_event(initial_state, "SIM_START", "SIM_CORE", {"message": "Simulation starting."})
    print("\n--- Running Simulation ---")
    env.run(until=SIMULATION_DURATION_DAYS)
    print("\n--- Simulation Complete ---")
    log_event(initial_state, "SIM_END", "SIM_CORE", {"message": f"Simulation ended at day {env.now:.2f}."})

    # 5. Output the final event log
    output_filename = "simulation_log.json"
    with open(output_filename, 'w') as f:
        json.dump(initial_state.event_log, f, indent=2)

    print(f"\nFull simulation log saved to {output_filename}")

if __name__ == "__main__":
    main()
