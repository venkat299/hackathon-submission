import random
from utils import log_event, distill_context, parse_llm_response
from config import PLAN_ADHERENCE_PROBABILITY, AVG_DAYS_PER_MEMBER_QUESTION, LOCS, MEMBER_PROFILE
import json

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

def health_issues_process(env, state):
    """
    Probabilistically simulates the onset of minor health issues based on the member's
    state, travel, and lifestyle.
    """
    yield env.timeout(1) # Delay start
    while True:
        yield env.timeout(1) # Run this check once per day

        if state.narrative_flags.get('active_issue') and state.current_day >= state.narrative_flags.get('issue_resolves_on', -1):
            resolved_issue = state.narrative_flags.pop('active_issue')
            state.narrative_flags.pop('issue_resolves_on')
            log_event(state, "HEALTH_ISSUE_RESOLVED", "SIM_CORE", {"issue": resolved_issue})

        if 'issue_cooldown_until' in state.narrative_flags and state.current_day < state.narrative_flags['issue_cooldown_until']:
            continue

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
    days_deviated = 0
    while True:
        yield env.timeout(1) # Run once per day
        trigger_event, responder = None, None
        last_event = state.event_log[-1] if state.event_log else None
        live_data = state.health_data.wearable_stream

        # --- Update Adherence Status ---
        if random.random() > PLAN_ADHERENCE_PROBABILITY:
            if state.intervention_plan.adherence_status == "ON_TRACK":
                state.intervention_plan.adherence_status = "DEVIATED"
                days_deviated = 1
            else:
                days_deviated += 1
        else:
            state.intervention_plan.adherence_status = "ON_TRACK"
            days_deviated = 0
        
        # --- ACTION-ORIENTED & HIGH-PRIORITY TRIGGERS ---
        # **NEW** Travel Check-in Trigger
        if last_event and last_event['type'] == 'TRAVEL_START' and not state.narrative_flags.get('travel_check_in_sent'):
            responder = "Ruby"
            trigger_event = f"""
            TRAVEL CHECK-IN: Rohan has just started traveling to {state.logistics.location}.
            TASK: Write a brief, proactive message to acknowledge his trip. Offer a practical, health-related tip for traveling (e.g., hydration, sleep) and wish him a safe journey.
            """
            state.narrative_flags['travel_check_in_sent'] = True
        elif last_event and last_event['type'] == 'TRAVEL_END':
            state.narrative_flags.pop('travel_check_in_sent', None)

        elif state.narrative_flags.get('status') == "Onboarding" and not state.narrative_flags.get('onboarding_docs_sent'):
            responder = "Ruby"
            trigger_event = "Action: Send the onboarding documents and data request to Rohan."
            state.narrative_flags['onboarding_docs_sent'] = True
        
        elif state.narrative_flags.get('active_issue'):
            issue = state.narrative_flags['active_issue']
            if "Strain" in issue: responder = "Rachel"
            elif "Illness" in issue or "Pressure" in issue: responder = "Dr. Warren"
            elif "Indigestion" in issue: responder = "Carla"
            else: responder = "Dr. Warren"
            trigger_event = f"""
            CRITICAL HEALTH ALERT: Rohan is experiencing '{issue}'.
            ANALYZE LIVE DATA: {json.dumps(live_data)}
            TASK: Formulate a response that acknowledges his issue, interprets the data, provides a clear, actionable recommendation, and determines a next step (e.g., 'INITIATE_SICK_DAY_PROTOCOL', 'FLAG_FOR_EXPERT').
            """
        
        elif last_event and last_event['type'] == 'POSITIVE_MILESTONE':
            responder = "Neel"
            trigger_event = f"""
            POSITIVE MILESTONE REACHED: Rohan just achieved '{last_event['payload']['milestone']}'.
            TASK: As the team leader, write a strategic and reassuring message of congratulations. Connect this specific milestone back to his larger, long-term goals to reinforce the value of the program.
            """
        
        # --- RUBY'S LESS FREQUENT, DIVERSE TRIGGERS ---
        elif days_deviated >= 3 and not state.narrative_flags.get('adherence_check_sent'):
            responder = "Ruby"
            trigger_event = f"""
            PROACTIVE ADHERENCE CHECK-IN: The system flagged that Rohan may have deviated from the plan for a few days.
            TASK: Write an empathetic, organized, and proactive message. Do not be accusatory. Gently check in and ask if there are any logistical barriers or scheduling issues you can help with to get him back on track.
            """
            state.narrative_flags['adherence_check_sent'] = True
        elif days_deviated == 0:
             state.narrative_flags.pop('adherence_check_sent', None)


        elif state.current_day > 0 and state.current_day % 45 < 1 and not state.narrative_flags.get('wellness_check_sent'):
            responder = "Ruby"
            trigger_event = f"""
            PERIODIC WELLNESS CHECK-IN: It's been a while.
            TASK: Write a brief, friendly, and open-ended message to check in on Rohan's general well-being. This is not about data or adherence, but about him as a person. Ask how he's feeling overall.
            """
            state.narrative_flags['wellness_check_sent_day'] = state.current_day


        # --- REGULAR, DATA-DRIVEN CHECK-INS (Other Experts) ---
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

        if trigger_event and responder:
            # Reset the wellness check flag to allow it in the next cycle
            if 'wellness_check_sent_day' in state.narrative_flags and state.current_day > state.narrative_flags['wellness_check_sent_day']:
                state.narrative_flags.pop('wellness_check_sent_day', None)
            
            context = distill_context(state, responder)
            try:
                prediction = elyx_agents[responder](context=context, trigger=trigger_event)
                
                message, action = parse_llm_response(prediction.response)

                if message:
                    log_event(state, "MESSAGE", responder, {"content": message})
                    if responder not in state.agent_memory:
                        state.agent_memory[responder] = []
                    state.agent_memory[responder].append(message)
                    state.agent_memory[responder] = state.agent_memory[responder][-5:]

                if action and action.get("type") != "NONE":
                    log_event(state, "ACTION_EXECUTED", f"{responder}_AGENT", {"action": action})
                    if action["type"] == "UPDATE_NARRATIVE_FLAG":
                        state.narrative_flags[action["payload"]["flag"]] = action.get("payload", {})

            except Exception as e:
                log_event(state, "ERROR", f"{responder}_AGENT", {"error": str(e)})

def member_process(env, state, member_agent, elyx_agents, router):
    """
    Models Rohan's behavior. He can either reply to a recent message
    or proactively initiate a new conversation.
    """
    yield env.timeout(0.1)
    while True:
        time_to_next_action = random.expovariate(1.0 / AVG_DAYS_PER_MEMBER_QUESTION)
        yield env.timeout(time_to_next_action)

        context = distill_context(state, "Rohan")
        last_event = state.event_log[-1] if state.event_log else None
        
        should_reply = False
        if last_event and last_event['type'] == 'MESSAGE' and last_event['source'] != 'Rohan':
            last_rohan_message_day = -1
            for event in reversed(state.event_log):
                if event['source'] == 'Rohan':
                    last_rohan_message_day = event['day']
                    break
            if last_event['day'] > last_rohan_message_day:
                should_reply = True

        try:
            if should_reply:
                # --- BEHAVIOR 1: GENERATE A REPLY ---
                last_message_content = last_event['payload']['content']
                last_message_source = last_event['source']
                
                prediction = member_agent.reply(context=context, last_message=last_message_content)
                raw_json = prediction.reply
                reply_text = ""
                try:
                    reply_text = json.loads(raw_json).get("reply", raw_json)
                except (json.JSONDecodeError, AttributeError):
                    reply_text = raw_json.strip()

                if reply_text:
                    log_event(state, "MESSAGE", "Rohan", {"content": reply_text, "in_reply_to": last_message_source})
                    if "Rohan" not in state.agent_memory:
                        state.agent_memory["Rohan"] = []
                    state.agent_memory["Rohan"].append(reply_text)
                    state.agent_memory["Rohan"] = state.agent_memory["Rohan"][-5:]
            
            else:
                # --- BEHAVIOR 2: INITIATE A NEW QUESTION (Original Logic) ---
                prediction = member_agent(context=context)
                raw_json = prediction.question
                question_text = ""
                try:
                    question_text = json.loads(raw_json).get("question", raw_json)
                except (json.JSONDecodeError, AttributeError):
                    question_text = raw_json.strip()

                if not question_text:
                    continue

                log_event(state, "MESSAGE", "Rohan", {"content": question_text})
                if "Rohan" not in state.agent_memory:
                    state.agent_memory["Rohan"] = []
                state.agent_memory["Rohan"].append(question_text)
                state.agent_memory["Rohan"] = state.agent_memory["Rohan"][-5:]
                
                yield env.timeout(random.uniform(0.01, 0.1))
                
                conv_history = "\n".join([f"- {evt['source']}: {evt['payload']['content']}" for evt in state.event_log if evt['type'] == 'MESSAGE'][-5:])
                routing_prediction = router(question=question_text, conversation_history=conv_history)
                
                responder = routing_prediction.expert_name
                if responder not in elyx_agents:
                    responder = "Ruby"

                log_event(state, "ROUTING", "SIM_CORE", {"question": question_text, "routed_to": responder, "method": "semantic_llm"})
                
                context_after_question = distill_context(state, responder)
                response_prediction = elyx_agents[responder](context=context_after_question, trigger=f"Rohan asked: {question_text}")
                
                message, action = parse_llm_response(response_prediction.response)
                
                if message:
                    log_event(state, "MESSAGE", responder, {"content": message})
                    if responder not in state.agent_memory:
                        state.agent_memory[responder] = []
                    state.agent_memory[responder].append(message)
                    state.agent_memory[responder] = state.agent_memory[responder][-5:]

                if action and action.get("type") != "NONE":
                    log_event(state, "ACTION_EXECUTED", f"{responder}_AGENT", {"action": action})
                    if action["type"] == "UPDATE_NARRATIVE_FLAG":
                        state.narrative_flags[action["payload"]["flag"]] = action.get("payload", {})

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

def dialog_flow_process(env, state):
    """
    Observes conversations for topic stagnation and intervenes to redirect the conversation
    towards the member's broader goals.
    """
    topic_keywords = {
        "heart_health": ["cholesterol", "blood pressure", "heart", "cardio"],
        "cognitive_function": ["cognitive", "focus", "mental performance", "brain"],
        "screenings": ["screening", "full-body", "detection", "test"],
    }
    last_intervention_day = -10 # Cooldown to prevent spamming interventions
    
    yield env.timeout(1) # Delay start
    while True:
        yield env.timeout(0.5) # Check every 12 simulation hours

        if state.current_day - last_intervention_day < 3: # 3-day cooldown
            continue

        rohan_messages = [
            event['payload']['content'] for event in state.event_log 
            if event['source'] == 'Rohan'
        ][-3:] # Look at last 3 questions

        if len(rohan_messages) < 3:
            continue

        stalled_topic = None
        message_topics = []

        for msg in rohan_messages:
            msg_topic = "general"
            for topic, keywords in topic_keywords.items():
                if any(keyword in msg.lower() for keyword in keywords):
                    msg_topic = topic
                    break
            message_topics.append(msg_topic)

        # Check if the last 3 questions were about the same non-general topic
        if len(set(message_topics)) == 1 and message_topics[0] != "general":
            stalled_topic = message_topics[0]
        
        if stalled_topic:
            # Identify a different goal to pivot to
            all_goals = list(MEMBER_PROFILE['goals'])
            stalled_goal_phrase = None
            
            if "heart" in stalled_topic: stalled_goal_phrase = "heart disease"
            elif "cognitive" in stalled_topic: stalled_goal_phrase = "cognitive function"
            elif "screening" in stalled_topic: stalled_goal_phrase = "health screenings"
            
            # Find a goal that is NOT the stalled one
            next_goal_suggestion = "another of your health priorities"
            for goal in all_goals:
                if stalled_goal_phrase and stalled_goal_phrase not in goal:
                    next_goal_suggestion = f"your goal of '{goal.strip()}'"
                    break

            intervention_message = (
                f"I've noticed our conversation is focused on {stalled_topic.replace('_', ' ')}. "
                f"To ensure we're making progress on all fronts, shall we pivot to {next_goal_suggestion}?"
            )
            
            log_event(state, "DIALOG_INTERVENTION", "DIALOG_FLOW_AGENT", {"message": intervention_message})
            last_intervention_day = state.current_day