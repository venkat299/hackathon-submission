# venkat299/med-data-generation/med-data-generation-iter-7/main.py
import simpy
import dspy
import os
import json
from dotenv import load_dotenv
import datetime

from models.state import SimulationState, MemberProfile
# Import the new Router module
from agents.modules import Agent, MemberAgent, Router
from simulation.processes import (
    timeline_process, member_process, proactive_expert_process,
    state_update_process, health_issues_process, milestone_process
)
from config import (
    SIMULATION_DURATION_DAYS, MEMBER_PROFILE, AGENT_PERSONAS, LLM_ENABLED,
    LLM_PROVIDER, LOCAL_LLM_MODEL, LOCAL_LLM_BASE_URL, LOCAL_LLM_API_KEY,
    GOOGLE_LLM_MODEL
)
from utils import log_event, get_simulation_timestamp

class ClockUpdater:
    def __init__(self, env, state):
        self.env, self.state, self.process = env, state, env.process(self.run())
    def run(self):
        while True:
            self.state.current_day = self.env.now
            yield self.env.timeout(0.01)

def setup_dspy():
    load_dotenv()
    if LLM_PROVIDER == "local":
        print(f"--- Configuring for local LLM: {LOCAL_LLM_MODEL} ---")
        lm = dspy.LM(
            model=LOCAL_LLM_MODEL,
            base_url=LOCAL_LLM_BASE_URL,
            api_key=LOCAL_LLM_API_KEY
        )
    elif LLM_PROVIDER == "google":
        print(f"--- Configuring for Google LLM: {GOOGLE_LLM_MODEL} ---")
        lm = dspy.LM(
            model=GOOGLE_LLM_MODEL,
            api_key=os.getenv("GOOGLE_API_KEY")
        )
    else:
        raise ValueError(f"Invalid LLM_PROVIDER in config: {LLM_PROVIDER}")

    dspy.configure(lm=lm)

def write_chat_log(event_log, filename):
    """Filters for MESSAGE events and writes them to a human-readable chat log."""
    with open(filename, 'w') as f:
        f.write("--- WhatsApp Chat Log ---\n\n")
        for event in event_log:
            if event['type'] == 'MESSAGE':
                timestamp = event['timestamp']
                source = event['source']
                content = event['payload']['content']
                f.write(f"[{timestamp}] {source}: {content}\n")

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

    # --- Create timestamped log files ---
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    full_log_filename = f"simulation_log_{timestamp_str}.json"
    chat_log_filename = f"whatsapp_chat_{timestamp_str}.txt"

    # Save the full, detailed event log
    with open(full_log_filename, 'w') as f:
        json.dump(initial_state.event_log, f, indent=2)
    print(f"\nFull simulation log saved to {full_log_filename}")

    # Save the clean, readable chat log
    write_chat_log(initial_state.event_log, chat_log_filename)
    print(f"WhatsApp chat log saved to {chat_log_filename}")


if __name__ == "__main__":
    main()