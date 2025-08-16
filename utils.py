import json
from config import SIMULATION_START_DATE
import datetime

def get_simulation_timestamp(current_day: float) -> str:
    """Converts simulation days to a formatted date string."""
    delta = datetime.timedelta(days=current_day)
    timestamp = SIMULATION_START_DATE + delta
    return timestamp.strftime("%m/%d/%y, %I:%M %p")

def log_event(state, event_type: str, source: str, payload: dict):
    """Creates a structured log entry and appends it to the state's event log."""
    timestamp_str = get_simulation_timestamp(state.current_day)
    log_entry = {
        "day": round(state.current_day, 2),
        "timestamp": timestamp_str,
        "type": event_type,
        "source": source,
        "payload": payload
    }
    state.event_log.append(log_entry)
    # Print in real-time for observation
    print(f"{timestamp_str} | {source}: {payload.get('content', json.dumps(payload))}")

def distill_context(state, agent_name: str, max_history: int = 15) -> str:
    """
    Creates a concise summary of the current state and recent history for the LLM.
    """
    # 1. Get current state summary
    state_summary = f"""
Current State (Day {state.current_day:.1f}):
- Member: {state.member_profile.name}, Age: {state.member_profile.age}
- Location: {state.logistics.location} {'(Traveling)' if state.logistics.is_traveling else ''}
- Active Health Issues: {state.narrative_flags.get('active_issue', 'None')}
- Current Goals: {'; '.join(state.member_profile.goals)}
- Adherence: {state.intervention_plan.adherence_status}
- Narrative Flags: {json.dumps(state.narrative_flags)}
"""

    # 2. --- NEW: Summarize critical recent DES events from the last day ---
    critical_events_summary = ""
    non_message_events = [
        event for event in state.event_log
        if event['type'] != 'MESSAGE' and (state.current_day - event['day']) <= 1.0
    ]
    if non_message_events:
        critical_events_summary = "## CRITICAL RECENT EVENTS (Last 24 Hours) ##\n"
        for event in non_message_events:
            critical_events_summary += f"- Event: {event['type']}, Details: {json.dumps(event['payload'])}\n"

    # 3. Get recent conversation history
    recent_history = ""
    message_events = [event for event in state.event_log if event['type'] == 'MESSAGE']
    last_events = message_events[-max_history:]
    for event in last_events:
        recent_history += f"- {event['source']}: {event['payload']['content']}\n"

    # 4. Get this agent's own history
    agent_history = "\n".join(state.agent_memory.get(agent_name, []))

    # 5. Assemble the full context
    full_context = f"""
{critical_events_summary if critical_events_summary else ''}
## CONTEXT ##
{state_summary}

## YOUR ( {agent_name} ) RECENT MESSAGES ##
{agent_history if agent_history else "You have not sent any messages recently."}

## OVERALL RECENT CONVERSATION ##
{recent_history if recent_history else "No recent conversation."}
"""
    return full_context

# --- NEW ROBUST PARSER FUNCTION ---
def parse_llm_response(raw_response: str) -> (str, dict):
    """
    Safely parses the LLM's response.
    Handles both valid JSON and plain string fallbacks.
    Returns a tuple of (message, action).
    """
    try:
        # Attempt to parse the full string as JSON
        response_obj = json.loads(raw_response)
        message = response_obj.get("message", "")
        action = response_obj.get("action", {"type": "NONE"})
        return message, action
    except (json.JSONDecodeError, AttributeError, TypeError):
        # If parsing fails, assume the entire raw response is the message
        # and there is no action.
        return raw_response, {"type": "NONE"}