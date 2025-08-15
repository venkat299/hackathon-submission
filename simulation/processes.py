import random
from utils import log_event, distill_context, parse_llm_response
from config import PLAN_ADHERENCE_PROBABILITY, AVG_DAYS_PER_MEMBER_QUESTION, LOCS
import json

# --- Scripted scenario timeline -------------------------------------------------
# These events provide a deterministic backbone for the simulation so that key
# narrative beats happen on fixed days.  Each event dictionary must at least
# define a ``day`` and ``type``.  Additional fields are interpreted by the
# processes that consume them (e.g., ``issue`` and ``duration`` for ILLNESS
# events).
SCENARIO_TIMELINE = [
    {"day": 7, "type": "ILLNESS", "issue": "Minor Illness (Cold/Flu)", "duration": 3},
    {"day": 14, "type": "THERAPY_SESSION", "provider": "Physical Therapist"},
    {"day": 30, "type": "MILESTONE", "milestone": "30-day progress check"},
]
def timeline_process(env, state):
    """Schedules all deterministic and periodic events based on the high-level plan."""
    # Initial onboarding
    state.narrative_flags['status'] = "Onboarding"
    log_event(state, "STATE_CHANGE", "SIM_CORE", {"status": "Onboarding started"})
    yield env.timeout(28) # 4 weeks for onboarding

    state.narrative_flags['status'] = "Intervention"
    log_event(state, "STATE_CHANGE", "SIM_CORE", {"status": "Main intervention phase started"})

    # Schedule recurring events in parallel
    env.process(diagnostic_test_process(env, state))
    env.process(exercise_plan_update_process(env, state))
    env.process(travel_process(env, state))

def diagnostic_test_process(env, state):
    """Schedules a full diagnostic test panel every three months."""
    while True:
        yield env.timeout(90) # Every 3 months
        log_event(state, "DIAGNOSTIC_TEST", "SIM_CORE", {"description": "Quarterly diagnostic test panel initiated."})
        state.health_data.lab_results = {
            "cholesterol": round(random.uniform(150, 220), 1),
            "blood_pressure": f"{random.randint(110, 130)}/{random.randint(70, 85)}",
            "last_test_day": state.current_day
        }

def exercise_plan_update_process(env, state):
    """Triggers an exercise plan review and update every two weeks."""
    while True:
        yield env.timeout(14) # Every 2 weeks
        state.intervention_plan.last_exercise_update_day = state.current_day
        log_event(state, "PLAN_UPDATE", "SIM_CORE", {"description": "Exercise plan updated."})

def travel_process(env, state):
    """Manages the travel schedule, setting the is_traveling flag."""
    while True:
        yield env.timeout(21)
        state.logistics.is_traveling = True
        state.logistics.location = random.choice(LOCS)
        log_event(state, "TRAVEL_START", "SIM_CORE", {"location": state.logistics.location})
        yield env.timeout(7)
        state.logistics.is_traveling = False
        state.logistics.location = "Singapore"
        # Corrected Typo Here
        log_event(state, "TRAVEL_END", "SIM_CORE", {"location": "Singapore"})

def health_issues_process(env, state, scenario=SCENARIO_TIMELINE):
    """Handles deterministic health/story events and falls back to random issues.

    The process first checks the :data:`SCENARIO_TIMELINE` for any scripted events
    scheduled for the current day.  If none are found, it uses probabilistic logic
    to potentially introduce a minor health issue based on lifestyle factors.
    """
    yield env.timeout(1)  # Delay start
    scenario_queue = sorted(list(scenario), key=lambda e: e["day"])  # work on a copy

    while True:
        yield env.timeout(1)  # Run this check once per day

        # --- Resolve existing issues -------------------------------------------------
        if state.narrative_flags.get('active_issue') and state.current_day >= state.narrative_flags.get('issue_resolves_on', -1):
            resolved_issue = state.narrative_flags.pop('active_issue')
            state.narrative_flags.pop('issue_resolves_on')
            log_event(state, "HEALTH_ISSUE_RESOLVED", "SIM_CORE", {"issue": resolved_issue})

        # --- Handle scripted events --------------------------------------------------
        while scenario_queue and scenario_queue[0]["day"] == state.current_day:
            event = scenario_queue.pop(0)
            if event["type"] == "ILLNESS":
                issue = event["issue"]
                duration = event.get("duration", 3)
                state.narrative_flags['active_issue'] = issue
                state.narrative_flags['issue_resolves_on'] = state.current_day + duration
                state.narrative_flags['issue_cooldown_until'] = state.current_day + duration + 7
                log_event(state, "HEALTH_ISSUE", "SIM_CORE", {"issue": issue, "scripted": True, "duration_days": duration})
            elif event["type"] == "THERAPY_SESSION":
                state.narrative_flags['therapy_session_today'] = True
                log_event(state, "THERAPY_SESSION", "SIM_CORE", {"provider": event.get("provider", "Therapist")})
            elif event["type"] == "MILESTONE":
                log_event(state, "POSITIVE_MILESTONE", "SIM_CORE", {"milestone": event.get("milestone", "Milestone reached")})

        # Skip random generation if cooling down or an issue already active
        if state.narrative_flags.get('active_issue') or (
            'issue_cooldown_until' in state.narrative_flags and state.current_day < state.narrative_flags['issue_cooldown_until']
        ):
            continue

        # --- Probabilistic fallback --------------------------------------------------
        PROBS = {
            "Minor Illness (Cold/Flu)": 0.005, "Muscle Strain/Joint Pain": 0.004,
            "Bout of Indigestion": 0.007, "Stress Headache": 0.006, "Blood Pressure Spike": 0.003
        }
        risk_modifiers = {key: 0.0 for key in PROBS}
        recovery = state.health_data.wearable_stream.get("recovery_score", 100)

        if state.logistics.is_traveling:
            risk_modifiers["Minor Illness (Cold/Flu)"] += 0.025
            risk_modifiers["Bout of Indigestion"] += 0.03
            risk_modifiers["Stress Headache"] += 0.01

        if recovery < 40:
            risk_modifiers["Minor Illness (Cold/Flu)"] += 0.015
            risk_modifiers["Muscle Strain/Joint Pain"] += 0.02
            risk_modifiers["Stress Headache"] += 0.015
            risk_modifiers["Blood Pressure Spike"] += 0.01

        if state.intervention_plan.adherence_status == "DEVIATED":
            risk_modifiers["Blood Pressure Spike"] += 0.02
            risk_modifiers["Bout of Indigestion"] += 0.01

        for issue, base_prob in PROBS.items():
            if random.random() < (base_prob + risk_modifiers[issue]):
                duration = random.randint(2, 5)
                state.narrative_flags['active_issue'] = issue
                state.narrative_flags['issue_resolves_on'] = state.current_day + duration
                state.narrative_flags['issue_cooldown_until'] = state.current_day + duration + random.randint(7, 14)
                log_event(state, "HEALTH_ISSUE", "SIM_CORE", {
                    "issue": issue,
                    "triggering_factors": {"is_traveling": state.logistics.is_traveling, "recovery_score": recovery, "adherence": state.intervention_plan.adherence_status},
                    "duration_days": duration
                })
                break

def milestone_process(env, state):
    """Checks for and logs positive health and adherence milestones."""
    hrv_milestone = 50
    adherence_milestone_days = 30
    days_on_track = 0
    while True:
        yield env.timeout(1) # Check once per day
        if state.intervention_plan.adherence_status == "ON_TRACK":
            days_on_track += 1
        else:
            days_on_track = 0

        if days_on_track >= adherence_milestone_days:
            log_event(state, "POSITIVE_MILESTONE", "SIM_CORE", {"milestone": f"{adherence_milestone_days} consecutive days of adherence!"})
            days_on_track = 0
            adherence_milestone_days += 30

        if state.health_data.wearable_stream.get('hrv', 0) > hrv_milestone:
            log_event(state, "POSITIVE_MILESTONE", "SIM_CORE", {"milestone": f"Daily HRV surpassed {hrv_milestone}!"})
            hrv_milestone += 5

def proactive_expert_process(env, state, elyx_agents):
    """Embodies the proactive nature of the Elyx service by running enriched, data-driven checks daily."""
    state.narrative_flags.setdefault('consultation_scheduled', False)
    while True:
        yield env.timeout(1) # Run once per day
        trigger_event, responder = None, None
        last_event = state.event_log[-1] if state.event_log else None
        live_data = state.health_data.wearable_stream

        # --- ACTION-ORIENTED & HIGH-PRIORITY TRIGGERS ---
        if state.narrative_flags.get('status') == "Onboarding" and not state.narrative_flags.get('onboarding_docs_sent'):
            responder = "Ruby"
            trigger_event = "Action: Send the onboarding documents and data request to Rohan."
            state.narrative_flags['onboarding_docs_sent'] = True

        elif state.narrative_flags.get('active_issue'):
            issue = state.narrative_flags['active_issue']
            if "Strain" in issue: responder = "Rachel"
            elif "Illness" in issue or "Pressure" in issue: responder = "Dr. Warren"
            elif "Indigestion" in issue: responder = "Carla"
            else: responder = "Dr. Warren"

            if not state.narrative_flags.get('consultation_scheduled'):
                trigger_event = f"""
                CRITICAL HEALTH ALERT: Rohan is experiencing '{issue}'.
                ANALYZE LIVE DATA: {json.dumps(live_data)}
                TASK: Formulate a response that acknowledges his issue, interprets the data, provides a clear, actionable recommendation, and determines a next step (e.g., 'INITIATE_SICK_DAY_PROTOCOL', 'FLAG_FOR_EXPERT'). If you send a scheduling link, include an action to UPDATE_NARRATIVE_FLAG with flag 'consultation_scheduled' set to true.
                """
            else:
                trigger_event = f"""
                FOLLOW-UP: Rohan continues to experience '{issue}'.
                ANALYZE LIVE DATA: {json.dumps(live_data)}
                TASK: Offer guidance and support without sending any additional scheduling links.
                """
        

        elif last_event and last_event['type'] == 'POSITIVE_MILESTONE':
            responder = "Neel"
            trigger_event = f"""
            POSITIVE MILESTONE REACHED: Rohan just achieved '{last_event['payload']['milestone']}'.
            TASK: As the team leader, write a strategic and reassuring message of congratulations. Connect this specific milestone back to his larger, long-term goals to reinforce the value of the program.
            """
        
        # --- REGULAR, DATA-DRIVEN CHECK-INS ---
        elif live_data.get("recovery_score", 100) < 30:
            responder = "Advik"
            trigger_event = f"""
            CRITICAL HEALTH ALERT: Recovery score is critically low.
            ANALYZE LIVE DATA: {json.dumps(live_data)}
            TASK: Formulate a data-driven insight for Rohan and determine an appropriate action (e.g., recommend rest, flag for Dr. Warren).
            """
            
        elif abs(state.current_day - state.intervention_plan.last_exercise_update_day) < 1:
            responder = "Rachel"
            trigger_event = f"""
            PROACTIVE CHECK-IN: The exercise plan was just updated.
            CONTEXT: His adherence is currently '{state.intervention_plan.adherence_status}'.
            TASK: Write an encouraging, direct message checking in on the new plan. Ask a specific question about form or function.
            """
            
        elif state.current_day > 0 and state.current_day % 14 < 1:
            responder = "Carla"
            trigger_event = f"""
            PROACTIVE NUTRITION CHECK-IN (Bi-weekly).
            CONTEXT: Rohan's goals include cognitive function and heart health. He was recently traveling: {'Yes' if state.logistics.is_traveling else 'No'}.
            TASK: Write a practical, educational message to start a review of his nutrition. Connect your question back to one of his core goals or his recent travel.
            """

        elif state.current_day > 0 and state.current_day % 90 < 1:
            responder = "Neel"
            trigger_event = f"""
            PROACTIVE STRATEGIC REVIEW (Quarterly).
            CONTEXT: We are at a 90-day milestone. Rohan's primary goals are: {'; '.join(state.member_profile.goals)}.
            TASK: Write a strategic, big-picture message to Rohan. Acknowledge the milestone and connect the team's day-to-day work back to his highest-level goals. Reassure him of the long-term vision.
            """

        elif random.random() > PLAN_ADHERENCE_PROBABILITY:
             if state.intervention_plan.adherence_status == "ON_TRACK":
                state.intervention_plan.adherence_status = "DEVIATED"
                responder = "Ruby"
                trigger_event = f"""
                PROACTIVE ADHERENCE CHECK-IN: The system flagged that Rohan may have deviated from the plan.
                TASK: Write an empathetic, organized, and proactive message. Do not be accusatory. Gently check in and ask if there are any logistical barriers or scheduling issues you can help with to get him back on track.
                """
        else:
            state.intervention_plan.adherence_status = "ON_TRACK"

        if trigger_event and responder:
            context = distill_context(state)
            try:
                prediction = elyx_agents[responder](context=context, trigger=trigger_event)
                
                # --- USE ROBUST PARSER ---
                message, action = parse_llm_response(prediction.response)

                if message:
                    log_event(state, "MESSAGE", responder, {"content": message})

                if action and action.get("type") != "NONE":
                    log_event(state, "ACTION_EXECUTED", f"{responder}_AGENT", {"action": action})
                    if action["type"] == "UPDATE_NARRATIVE_FLAG":
                        state.narrative_flags[action["payload"]["flag"]] = action["payload"]["value"]

            except Exception as e:
                log_event(state, "ERROR", f"{responder}_AGENT", {"error": str(e)})

def member_process(env, state, member_agent, elyx_agents, router):
    """Models the agency and behavior of the client, Rohan Patel."""
    state.narrative_flags.setdefault('consultation_scheduled', False)
    # (This function is unchanged)
    yield env.timeout(0.1)
    while True:
        time_to_next_question = random.expovariate(1.0 / AVG_DAYS_PER_MEMBER_QUESTION)
        yield env.timeout(time_to_next_question)
        context = distill_context(state)
        try:
            prediction = member_agent(context=context)
            log_event(state, "MESSAGE", "Rohan", {"content": prediction.question})
            yield env.timeout(random.uniform(0.01, 0.1))
            
            # Use a simpler context for the lightweight router
            conv_history = "\n".join([f"- {evt['source']}: {evt['payload']['content']}" for evt in state.event_log if evt['type'] == 'MESSAGE'][-5:])
            routing_prediction = router(question=prediction.question, conversation_history=conv_history)
            
            responder = routing_prediction.expert_name
            if responder not in elyx_agents:
                responder = "Ruby"

            log_event(state, "ROUTING", "SIM_CORE", {"question": prediction.question, "routed_to": responder, "method": "semantic_llm"})
            
            
            context_after_question = distill_context(state)
            trigger = f"Rohan asked: {prediction.question}"
            if state.narrative_flags.get('consultation_scheduled'):
                trigger += " Note: A consultation has already been scheduled, so avoid sending another scheduling link."
            response_prediction = elyx_agents[responder](context=context_after_question, trigger=trigger)
            
            # --- USE ROBUST PARSER ---
            message, action = parse_llm_response(response_prediction.response)
            
            if message:
                log_event(state, "MESSAGE", responder, {"content": message})

            if action and action.get("type") != "NONE":
                log_event(state, "ACTION_EXECUTED", f"{responder}_AGENT", {"action": action})
                if action["type"] == "UPDATE_NARRATIVE_FLAG":
                    state.narrative_flags[action["payload"]["flag"]] = action["payload"]["value"]

        except Exception as e:
            log_event(state, "ERROR", "MEMBER_AGENT", {"error": str(e)})

def state_update_process(env, state):
    """A simple process to simulate dynamic changes to the world state."""
    while True:
        yield env.timeout(0.25) # every 6 hours
        vital_modifier = 0.6 if state.narrative_flags.get('active_issue') else 1.0
        base_hrv = (45 + (state.current_day / 30)) * vital_modifier
        hrv_noise = random.uniform(-5, 5)
        state.health_data.wearable_stream['hrv'] = round(base_hrv + hrv_noise, 1)
        base_recovery = 70 - (20 if state.logistics.is_traveling else 0)
        recovery_noise = random.uniform(-15, 15)
        state.health_data.wearable_stream['recovery_score'] = max(0, min(100, round((base_recovery + recovery_noise) * vital_modifier)))

# def member_process(env, state, member_agent, elyx_agents, router): # Added 'router'
#     """Models the agency and behavior of the client, Rohan Patel."""
#     yield env.timeout(0.1)
    
#     while True:
#         time_to_next_question = random.expovariate(1.0 / AVG_DAYS_PER_MEMBER_QUESTION)
#         yield env.timeout(time_to_next_question)

#         context = distill_context(state)
#         try:
#             prediction = member_agent(context=context)
#             log_event(state, "MESSAGE", "Rohan", {"content": prediction.question})

#             yield env.timeout(random.uniform(0.01, 0.1))
#             context_after_question = distill_context(state)
            
#             # --- Semantic Routing Logic ---
#             # Replace the entire if/elif block with a call to the AI router.
#             # routing_prediction = router(question=prediction.question)
#             routing_prediction = router(question=prediction.question, conversation_history=distill_context(state))

#             # Use the LLM's choice, with a safe fallback to Ruby.
#             responder = routing_prediction.expert_name
#             if responder not in elyx_agents:
#                 responder = "Ruby" # Default if the LLM hallucinates a name

#             # Add a log event to see the routing decision!
#             log_event(state, "ROUTING", "SIM_CORE", {
#                 "question": prediction.question,
#                 "routed_to": responder,
#                 "method": "semantic_llm"
#             })

#             response_prediction = elyx_agents[responder](context=context_after_question, trigger=f"Rohan asked: {prediction.question}")
#             log_event(state, "MESSAGE", responder, {"content": response_prediction.response})

#         except Exception as e:
#             log_event(state, "ERROR", "MEMBER_AGENT", {"error": str(e)})