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


# --- DSPy Signature for Event Extraction ---
class ExtractEventFromChat(dspy.Signature):
    """
    **SYSTEM INSTRUCTION: Your ONLY output must be a single, valid JSON object matching the schema below.**
    Analyze the 'current_message' (which is chat number {chat_number}) within the 'conversation_context'.
    Extract and structure the information into a single JSON object.
    Deduce the 'event_class', 'event_type', and other fields logically from the text.
    Determine the 'prev_reference_chat_number' by identifying which previous chat this message is a reply to. If it's a new topic, this should be 0.
    Summarize the provided 'conversation_context' into a concise text string for the 'prev_summarized_context' field.
    """
    
    conversation_context = dspy.InputField(desc="A summary of the last few processed events, including their chat numbers.")
    current_message = dspy.InputField(desc="The specific chat message to analyze. Format can be '[Timestamp] Actor: Message' or 'Timestamp | Actor: Message'.")
    member_profile = dspy.InputField(desc="JSON string providing context about the member.")
    chat_number = dspy.InputField(desc="The sequential number of the current chat message.")

    event_json = dspy.OutputField(
        desc="A single, valid JSON object representing the structured event. Do not output any other text.",
        prefix="{",
        json_schema={
            "timestamp": "string",
            "prev_reference_chat_number": "integer (The chat number this message is a reply to. 0 if it's not a direct reply.)",
            "prev_summarized_context": "string (A concise summary of the conversation history provided as context.)",
            "event_class": "string (e.g., 'consultation', 'health_event', 'intervention', 'logistics', 'deviation')",
            "event_type": "string (e.g., 'question_asked', 'recommendation_given', 'symptom_reported', 'diagnostic_test', 'scheduling')",
            "description": "string (A concise summary of the event from the message)",
            "reason_context": "string (Why this event occurred, based on the conversation)",
            "actor": "string (Who initiated this specific message, e.g., 'Rohan', 'Dr. Warren')",
            "outcome_decision": "string (What was decided or the immediate result of this message)",
            "duration_hours": "float (Estimate if mentioned, otherwise 0.0)",
            "consult_type": "string (e.g., 'doctor', 'nutritionist', 'logistics_coordinator', 'member_query', 'none')",
            "follow_up": "boolean (Does this message imply a follow-up is needed?)",
            "metadata": "object (JSON object for extra attributes like test results, locations, etc.)"
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
    Reads the chat history, handles multi-line messages, processes each message
    with the LLM, and writes the structured data to a CSV file.
    """
    # 1. Setup
    setup_dspy_local_llm()
    event_extractor = EventExtractor()
    context_summary = deque(maxlen=CONTEXT_WINDOW_SIZE)
    chat_counter = 0

    # 2. Define CSV structure
    csv_columns = [
        'chat_number', 'timestamp', 'prev_reference_chat_number', 'prev_summarized_context',
        'event_class', 'event_type', 'description', 'reason_context', 'actor',
        'outcome_decision', 'duration_hours', 'consult_type', 'follow_up', 'metadata'
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

            # 4. Process each extracted message block
            for message in messages:
                if not message or "SIM_CORE" in message:
                    continue 

                chat_counter += 1
                processed_message = re.sub(r'\s*\n\s*', ' ', message).strip()

                print(f"\n--- Processing Message {chat_counter} ---")
                print(f"Raw Input: {processed_message}")

                try:
                    current_context_list = list(context_summary)
                    
                    # Call the LLM to extract the event
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
                    
                    # Populate row data from LLM output
                    row_data = {col: event_data.get(col, '') for col in csv_columns}
                    row_data['chat_number'] = chat_counter
                    # Get the summarized context from the LLM's own output
                    row_data['prev_summarized_context'] = event_data.get('prev_summarized_context', '')


                    if isinstance(row_data['metadata'], dict):
                        row_data['metadata'] = json.dumps(row_data['metadata'])

                    writer.writerow(row_data)
                    print(f"Successfully processed and saved event: {row_data['event_type']}")

                    # Update context for the next iteration
                    context_summary.append({
                        "number": chat_counter,
                        "summary": f"On {row_data['timestamp']}, {row_data['actor']} discussed '{row_data['description']}', deciding '{row_data['outcome_decision']}'."
                    })

                except json.JSONDecodeError as e:
                    print(f"!! ERROR: Failed to decode JSON from LLM response. Error: {e}")
                    print(f"LLM Raw Output: {prediction.event_json}")
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
""")

    process_chat_history()
