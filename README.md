## Communication Message Generation Methodology

1. SimPy-driven timeline
   - The simulation starts from a configured date and runs for eight months, modeling Rohan's journey.
   - Deterministic and stochastic processes (diagnostic tests, exercise updates, travel, health issues, milestones) are scheduled to mirror real-world interactions.
2. Agent personas and LLM responses
   - Member and Elyx expert personas are defined with distinct roles and voices.
   - When questions arise or proactive check-ins are due, context is distilled from recent events and fed to LLM-backed agents to craft WhatsApp-style messages.
   - DSPy orchestrates these interactions, supplying structured prompts and handling multi-step reasoning.
   - The LLM layer is pluggable: the configuration can route requests to local open-source models such as Gemma 3 via LM Studio or to hosted APIs like Google Gemini or OpenAI.
3. Event logging and chat log creation
   - Every message and key state change is logged with a timestamp.
   - At the end of the run, the log is distilled into a readable chat transcript for further analysis.

## Member Journey Visualization Methodology (process_chat.py)

1. Parse simulation outputs
   - Load the structured event log and chat transcript produced by the simulation.
   - Organize messages by day, tagging them by source and topic (plan updates, lab results, travel, etc.).
2. Aggregate state data
   - Combine communication records with wearable metrics, lab markers, and adherence flags stored in the event log to build a day-by-day profile of the member.
3. Generate visual summaries
   - Produce timelines and snapshot views showing conversation volume, key interventions, and health metrics.
   - Enable queries for specific dates to understand the member's context and progress at that moment.

Here’s what the visulaisation looks like:

![App Preview](visualization/visualisation2.png)
![App Preview](visualization/visualize1.png)
