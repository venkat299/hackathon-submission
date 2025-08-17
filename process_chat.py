import dspy
import csv
import json
import os
import re
from collections import deque
from dotenv import load_dotenv

# --- Configuration ---
# Make sure you have a .env file with your local model details, or configure dspy directly.
# Example .env:
# LOCAL_LLM_URL="http://localhost:1234/v1"
# LOCAL_LLM_MODEL="local-model" # Model name your local server uses
# LOCAL_LLM_API_KEY="not-needed"

from config import (
    SIMULATION_DURATION_DAYS, MEMBER_PROFILE, AGENT_PERSONAS, LLM_ENABLED,
    LLM_PROVIDER, LOCAL_LLM_MODEL, LOCAL_LLM_BASE_URL, LOCAL_LLM_API_KEY,
    GOOGLE_LLM_MODEL
)

INPUT_CHAT_FILE = 'whatsapp.txt'
OUTPUT_CSV_FILE = 'structured_events.csv'
CONTEXT_WINDOW_SIZE = 5
DISABLE_LLM_CACHE = True

# --- Member Profile (for LLM context) ---
MEMBER_PROFILE = {
    "member_id": "Rohan_Patel_46",
    "persona": "Analytical, time-constrained executive focused on evidence-based health optimization.",
    "goals": [
        "Reduce risk of heart disease.",
        "Enhance cognitive function.",
        "Implement annual health screenings."
    ]
}

# --- DSPy Configuration ---
def setup_dspy_local_llm():
    load_dotenv()
    http_headers = {}
    if DISABLE_LLM_CACHE:
        http_headers = {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        print("LLM caching is disabled.")


    if LLM_PROVIDER == "local":
        print(f"--- Configuring for local LLM: {LOCAL_LLM_MODEL} ---")
        lm = dspy.LM(
            model=LOCAL_LLM_MODEL,
            base_url=LOCAL_LLM_BASE_URL,
            api_key=LOCAL_LLM_API_KEY,
            headers=http_headers
        )
    elif LLM_PROVIDER == "google":
        print(f"--- Configuring for Google LLM: {GOOGLE_LLM_MODEL} ---")
        lm = dspy.LM(
            model=GOOGLE_LLM_MODEL,
            api_key=os.getenv("GOOGLE_API_KEY"),
            headers=http_headers
        )
    else:
        raise ValueError(f"Invalid LLM_PROVIDER in config: {LLM_PROVIDER}")

    dspy.configure(lm=lm)


# --- DSPy Signature for Event Extraction ---
class ExtractEventFromChat(dspy.Signature):
    """
    **SYSTEM INSTRUCTION: Your ONLY output must be a single, valid JSON object matching the schema below. All fields are mandatory.**

    **Task**: Analyze the 'current_message' within the 'conversation_context' and structure it into a JSON object.

    **Column Explanations**:
    - **is_significant**: A boolean (true/false). Set to 'true' if the event is important for plotting a health journey.
        - SIGNIFICANT event_classes: 'travel', 'health_event', 'intervention', 'deviation'.
        - SIGNIFICANT event_types: 'symptom_reported', 'diagnostic_test', 'therapy', 'medication_change', 'hospital_visit', 'consult', 'missed_consult'.
        - If the event belongs to any of these, set 'is_significant' to true. Otherwise, false.
    - **event_class**: The broad category of the event. This is the parent category.
        - 'health_event': Related to the member's physical or mental state (e.g., symptoms, feelings).
        - 'intervention': An action taken by the care team to guide the member (e.g., giving advice, changing a plan).
        - 'consultation': A direct interaction or conversation (e.g., asking a question, scheduling).
        - 'logistics': Administrative tasks (e.g., sending documents, reminders).
        - 'deviation': The member is not following the plan.
        - 'travel': Related to the member traveling.
    - **event_type**: The specific sub-type of the event_class.
        - Examples for 'health_event': 'symptom_reported', 'feeling_expressed'.
        - Examples for 'intervention': 'recommendation_given', 'plan_updated', 'medication_change'.
        - Examples for 'consultation': 'question_asked', 'consult_scheduled', 'information_request'.
        - Examples for 'logistics': 'document_sent', 'reminder_sent'.

    **Few-shot Examples**:
    1.  **Message**: "[01/15/25, 05:02 PM] Rohan: Given my goals, what's the most efficient initial step we can take?"
        **Output Hint**: 'is_significant' is true. This is a 'consultation' where a 'question_asked' is the specific event.
    2.  **Message**: "[01/15/25, 05:45 PM] Advik: Best first move: a 7-day HRV baseline."
        **Output Hint**: 'is_significant' is true. This is an 'intervention' where a 'recommendation_given' is the specific event.
    3.  **Message**: "[01/15/25, 11:45 PM] Ruby: Perfect, I’ll send onboarding docs tonight."
        **Output Hint**: 'is_significant' is false. This is a 'logistics' event where the 'event_type' is 'document_sent'.
    """
    
    conversation_context = dspy.InputField(desc="A summary of the last few processed events, including their global chat numbers.")
    current_message = dspy.InputField(desc="The specific chat message to analyze.")
    member_profile = dspy.InputField(desc="JSON string providing context about the member.")
    chat_number = dspy.InputField(desc="The global chat number of the current message.")

    event_json = dspy.OutputField(
        desc="A single, valid JSON object representing the structured event. Do not output any other text.",
        prefix="{",
        json_schema={
            "type": "object",
            "properties": {
                "is_significant": {"type": "boolean"},
                "timestamp": {"type": "string"},
                "event_class": {"type": "string"},
                "event_type": {"type": "string"},
                "description": {"type": "string"},
                "reason_context": {"type": "string"},
                "actor": {"type": "string"},
                "outcome_decision": {"type": "string"},
                "duration_hours": {"type": "number"},
                "consult_type": {"type": "string"},
                "follow_up": {"type": "boolean"},
                "metadata": {"type": "object"}
            },
            "required": [
                "is_significant", "timestamp", "event_class", "event_type",
                "description", "reason_context", "actor", "outcome_decision",
                "duration_hours", "consult_type", "follow_up", "metadata"
            ]
        }
    )

# --- DSPy Module ---
class EventExtractor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.extractor = dspy.Predict(ExtractEventFromChat)

    def forward(self, conversation_context, current_message, member_profile, chat_number):
        context_str = "\n".join(f"- Chat #{item['number']}: {item['summary']}" for item in conversation_context)
        profile_str = json.dumps(member_profile, indent=2)
        
        prediction = self.extractor(
            conversation_context=context_str,
            current_message=current_message,
            member_profile=profile_str,
            chat_number=chat_number
        )
        return prediction

# --- Main Script Logic ---
def process_chat_history():
    """
    Reads chat history, processes messages one-by-one with an LLM,
    and writes the structured data to a CSV file.
    """
    # 1. Setup
    setup_dspy_local_llm()
    event_extractor = EventExtractor()
    context_summary = deque(maxlen=CONTEXT_WINDOW_SIZE)
    chat_counter = 0

    # --- Clear previous output file ---
    if os.path.exists(OUTPUT_CSV_FILE):
        os.remove(OUTPUT_CSV_FILE)
        print(f"Cleared previous output file: '{OUTPUT_CSV_FILE}'")

    # 2. Define CSV structure
    csv_columns = [
        'is_significant', 'chat_number', 'timestamp', 'event_class', 'event_type',
        'description', 'reason_context', 'actor', 'outcome_decision',
        'duration_hours', 'consult_type', 'follow_up', 'metadata'
    ]

    # 3. Read input and open output
    try:
        with open(INPUT_CHAT_FILE, 'r', encoding='utf-8') as infile, \
             open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as outfile:
            
            writer = csv.DictWriter(outfile, fieldnames=csv_columns)
            writer.writeheader()

            print(f"\nProcessing chat history from '{INPUT_CHAT_FILE}'...")
            
            full_content = infile.read()
            message_blocks = re.split(r'(\[\d{2}/\d{2}/\d{2}, \d{2}:\d{2} [AP]M\]|\d{2}/\d{2}/\d{2}, \d{2}:\d{2} [AP]M \|)', full_content)
            
            messages = []
            for i in range(1, len(message_blocks), 2):
                if i + 1 < len(message_blocks):
                    full_message = message_blocks[i] + message_blocks[i+1]
                    messages.append(full_message.strip())

            # 4. Process messages one by one
            for message in messages:
                if not message.strip():
                    continue

                chat_counter += 1
                processed_message = re.sub(r'\s*\n\s*', ' ', message).strip()
                
                print(f"\n--- Processing Message {chat_counter} ---")
                print(f"Raw Input: {processed_message}")

                try:
                    current_context_list = list(context_summary)
                    
                    prediction = event_extractor(
                        conversation_context=current_context_list,
                        current_message=processed_message,
                        member_profile=MEMBER_PROFILE,
                        chat_number=chat_counter
                    )
                    
                    raw_json_str = prediction.event_json
                    if raw_json_str.startswith("```json"):
                        raw_json_str = raw_json_str[7:].strip()
                    if raw_json_str.endswith("```"):
                        raw_json_str = raw_json_str[:-3].strip()
                    
                    event_data = json.loads(raw_json_str)
                    
                    # Populate row from LLM and constants
                    row_data = {col: event_data.get(col) for col in csv_columns if col != 'chat_number'}
                    row_data['chat_number'] = chat_counter

                    # Convert metadata to string for CSV
                    if isinstance(row_data.get('metadata'), dict):
                        row_data['metadata'] = json.dumps(row_data['metadata'])

                    writer.writerow(row_data)
                    print(f"  - Saved event for chat #{chat_counter}: {row_data.get('event_type')}")

                    context_summary.append({
                        "number": chat_counter,
                        "summary": f"On {row_data.get('timestamp')}, {row_data.get('actor')} discussed '{event_data.get('description', '')}', deciding '{event_data.get('outcome_decision', '')}'."
                    })

                except (json.JSONDecodeError, TypeError) as e:
                    print(f"!! ERROR: Failed to decode or process LLM response. Error: {e}")
                    print(f"LLM Raw Output: {prediction.event_json if 'prediction' in locals() else 'N/A'}")
                except Exception as e:
                    print(f"!! An unexpected error occurred: {e}")

            print(f"\nProcessing complete. Structured data saved to '{OUTPUT_CSV_FILE}'.")

    except FileNotFoundError:
        print(f"Error: Input file '{INPUT_CHAT_FILE}' not found.")
        print("Please create this file and populate it with the chat history.")

if __name__ == '__main__':
    # Create a dummy chat history file with the new format for demonstration
    if not os.path.exists(INPUT_CHAT_FILE):
        print(f"Creating a sample '{INPUT_CHAT_FILE}' for demonstration.")
        with open(INPUT_CHAT_FILE, 'w', encoding='utf-8') as f:
            f.write("""
[01/15/25, 05:02 PM] Rohan:
Given my goals, what's the most efficient initial step we can take? I don’t want to waste time on unnecessary data.

[01/15/25, 05:45 PM] Advik:
Best first move: a 7-day HRV baseline.
That tells us how your body is balancing stress and recovery — key for both heart health and focus.

[01/15/25, 05:48 PM] Advik:
Your Garmin tracks HRV, resting heart rate, and recovery trends. We'll pull that into a dashboard. From there, we can spot early risk signals.

[01/15/25, 11:45 PM] Ruby:
Perfect, I’ll send onboarding docs tonight 📑 — that includes:

Medical history form
Lifestyle intake (sleep, nutrition, movement, stress)
Permissions to pull wearable data

[01/16/25, 10:48 PM] Rohan:
Thanks. Send them over. I’ll skim, but I need a clear timeline — and I only want essential data first.

[01/17/25, 09:00 AM] Dr. Warren:
Rohan, the timeline is ready. The first phase focuses on establishing baselines for your key biomarkers. This is non-negotiable for tracking progress.

[01/17/25, 09:30 AM] Rohan:
Fine. What's the first test?
""")

    process_chat_history()
