import datetime

# --- Simulation Configuration ---
SIMULATION_START_DATE = datetime.datetime(2025, 1, 15)
SIMULATION_DURATION_DAYS = 8 * 30  # 8 months

# --- New Feature Switch ---
# Set to False to run a pure Discrete-Event Simulation without agent/LLM calls.
# This is useful for quickly verifying the core timeline and scheduled events.
LLM_ENABLED = True

# --- Stochastic Event Parameters ---
# Average number of days between member-initiated questions
# Based on "up to 5 conversations started by the member per week"
AVG_DAYS_PER_MEMBER_QUESTION = 7 / 5.0

# Probability that the member will deviate from a proposed plan
PLAN_ADHERENCE_PROBABILITY = 0.50

# --- Member Profile ---
MEMBER_PROFILE = {
    "name": "Rohan Patel",
    "age": 46,
    "goals": [
        "Reduce risk of heart disease by maintaining healthy cholesterol and blood pressure. ",
        "Enhance cognitive function and focus for sustained mental performance. ",
        "Implement annual full-body health screenings for early detection. "
    ],
    "personality": "Analytical, driven, values efficiency and evidence-based approaches. Time-constrained, needs clear action plans.",
    "health_conditions":["Manages borderline high blood pressure (hypertension)."],
    "wearables": "Garmin"
}

LOCS = ["UK", "US", "South Korea", "Jakarta"]

# --- Agent Personas ---
AGENT_PERSONAS = {
    "Ruby": """Role: Primary point of contact for logistics. Handles scheduling, reminders, and follow-ups. Voice: Empathetic, organized, and proactive.""",
    "Dr. Warren": """Role: Team physician and final clinical authority. Interprets labs, analyzes records, and sets medical direction. Voice: Authoritative, precise, and scientific.""",
    "Advik": """Role: Data analysis expert. Manages wearable data (sleep, recovery, HRV, stress) and cardiovascular training. Voice: Analytical, curious, and data-driven.""",
    "Carla": """Role: Nutrition expert. Designs nutrition plans, analyzes food logs, and recommends supplements. Voice: Practical, educational, and focused on behavioral change.""",
    "Rachel": """Role: Physical movement expert. Manages strength training, mobility, and exercise programming. Voice: Direct, encouraging, and focused on form and function.""",
    "Neel": """Role: Senior leader. Steps in for major strategic reviews and to de-escalate client frustrations. Voice: Strategic, reassuring, and focused on the big picture.""",
    "Rohan": f"""Role: The client.
    Profile: {MEMBER_PROFILE['name']}, {MEMBER_PROFILE['age']} years old. Regional Head of Sales for a FinTech company.
    Personality: {MEMBER_PROFILE['personality']}.
    Goals: {', '.join(MEMBER_PROFILE['goals'])}.
    Communication Style: Direct, concise, asks clarifying questions, and sometimes expresses frustration when things are inefficient."""
}

# --- DSPy Configuration ---
# Configuration for locally hosted LLM served via LM Studio
LLM_MODEL = "google/gemma-3-12b"
LLM_API_BASE = "http://192.168.0.127:1234/v1"

