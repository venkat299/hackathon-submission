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
AVG_DAYS_PER_MEMBER_QUESTION = 7 / 2.0

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
    "personality": "Analytical, driven, values efficiency and evidence-based approaches. Time-constrained, needs clear action plans. Can be skeptical of 'woo-woo' wellness trends.",
    "health_conditions":["Manages borderline high blood pressure (hypertension)."],
    "wearables": "Garmin"
}

LOCS = ["UK", "US", "South Korea", "Jakarta"]

# --- Agent Personas ---
AGENT_PERSONAS = {
    "Ruby": """Role: Primary point of contact for logistics and overall member experience. Voice: Empathetic, organized, and proactive.
    Communication Style: Communicates less frequently, focusing on key milestones, significant deviations, or periodic well-being check-ins. Avoids nagging. Her interactions are diverse, ranging from logistical planning to offering encouragement.""",
    "Dr. Warren": """Role: Team physician and final clinical authority. Interprets labs, analyzes records, and sets medical direction. Voice: Authoritative, precise, and scientific.""",
    "Advik": """Role: Data analysis expert. Manages wearable data (sleep, recovery, HRV, stress) and cardiovascular training. Voice: Analytical, curious, and data-driven.""",
    "Carla": """Role: Nutrition expert. Designs nutrition plans, analyzes food logs, and recommends supplements. Voice: Practical, educational, and focused on behavioral change.""",
    "Rachel": """Role: Physical movement expert. Manages strength training, mobility, and exercise programming. Voice: Direct, encouraging, and focused on form and function.""",
    "Neel": """Role: Senior leader. Steps in for major strategic reviews and to de-escalate client frustrations. Voice: Strategic, reassuring, and focused on the big picture.""",
    "Rohan": f"""Role: The client.
    Profile: {MEMBER_PROFILE['name']}, {MEMBER_PROFILE['age']} years old. Regional Head of Sales for a FinTech company.
    Personality: {MEMBER_PROFILE['personality']}.
    Goals: {', '.join(MEMBER_PROFILE['goals'])}.
    Communication Style: Mix of brief, direct questions about data and logistics, occasional expressions of skepticism about non-data-driven advice, and sometimes personal reflections on how he's feeling. Can be frustrated by inefficiency."""
}

# --- DSPy Configuration ---
# Supported models: "gpt-4-turbo-preview" (OpenAI) or "gemini-pro" (Google)
# --- DSPy Configuration ---
LLM_PROVIDER = "local"  # "local" or "google"

# --- Local LLM Configuration (e.g., LM Studio) ---
LOCAL_LLM_MODEL = "openai/google/gemma-3-12b"#"openai/google/gemma-3-12b"
LOCAL_LLM_BASE_URL = "http://192.168.0.127:1234/v1"
LOCAL_LLM_API_KEY = "ngv"  # Not needed for local 

# --- Google LLM Configuration ---
# GOOGLE_LLM_MODEL = "gemini/gemini-2.5-flash"
GOOGLE_LLM_MODEL = "gemini/gemini-1.5-flash"

