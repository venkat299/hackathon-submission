import dspy
from config import AGENT_PERSONAS

class GenerateResponse(dspy.Signature):
    """
    **SYSTEM INSTRUCTION: Your ONLY output must be a valid JSON object matching the schema below.**
    
    Generate a CONCISE, conversational, in-character response, like a WhatsApp message.
    The response should be brief and to the point, typically under 50 words.
    Avoid long explanations unless the user asks for details or it's a critical medical necessity.
    Review your own message history in the context to avoid repeating yourself.
    """
    persona = dspy.InputField(desc="The persona description for the agent.")
    context = dspy.InputField(desc="The current simulation state, critical events, and recent conversation history, including your own past messages.")
    trigger = dspy.InputField(desc="The specific event, data point, or message to respond to.")
    
    response = dspy.OutputField(
        desc="A flat JSON object containing 'message' and 'action' keys. This must be your only output.",
        prefix='{"message": "',
        json_schema={
            "message": "A very brief, WhatsApp-style message, under 50 words. Be direct. Do not provide long explanations unless explicitly asked or for critical medical reasons.",
            "action": {
                "type": "The type of action to take (e.g., 'INITIATE_SICK_DAY_PROTOCOL', 'FLAG_FOR_EXPERT', 'UPDATE_NARRATIVE_FLAG'). Must be 'NONE' if no action is taken.",
                "payload": "A dictionary with data for the action (e.g., {'expert_name': 'Dr. Warren'}, {'flag': 'consult_scheduled', 'value': true}). Must be an empty object {} if no action is taken."
            }
        }
    )

class GenerateMemberQuestion(dspy.Signature):
    """
    **SYSTEM INSTRUCTION: Your ONLY output must be a valid JSON object matching the schema below.**

    Given the member's persona and context, generate a diverse and in-character question or comment to initiate a conversation.
    The question should reflect different facets of the member's personality: analytical, skeptical, direct, or even reflective.
    Avoid asking repetitive questions. The question must be brief, between 5 and 50 words.
    """
    persona = dspy.InputField(desc="The persona description for the member.")
    context = dspy.InputField(desc="The current simulation state and recent conversation history, including your own past questions.")
    question = dspy.OutputField(
        desc="A flat JSON object with a single key 'question'. This must be your only output.",
        prefix='{"question": "',
        json_schema={"question": "A concise, in-character, and non-repetitive question or statement for the Elyx team, reflecting the member's diverse communication style."}
    )

class GenerateMemberReply(dspy.Signature):
    """
    **SYSTEM INSTRUCTION: Your ONLY output must be a valid JSON object matching the schema below.**

    Given the member's persona, the conversation context, and the last message they received, generate a direct and relevant reply.
    The reply should be concise and in-character.
    """
    persona = dspy.InputField(desc="The persona description for the member.")
    context = dspy.InputField(desc="The current simulation state and recent conversation history.")
    last_message = dspy.InputField(desc="The most recent message received by the member, which they need to reply to.")
    reply = dspy.OutputField(
        desc="A flat JSON object with a single key 'reply'. This must be your only output.",
        prefix='{"reply": "',
        json_schema={"reply": "A concise, in-character reply to the last message."}
    )


class RouteQuestion(dspy.Signature):
    """Given a user's question, recent conversation, and a list of expert roles, choose the best expert to respond."""
    question = dspy.InputField(desc="The user's most recent question.")
    conversation_history = dspy.InputField(desc="The last few messages in the conversation.")
    expert_roles = dspy.InputField(desc="A detailed list of available experts and their specific roles.")
    expert_name = dspy.OutputField(desc="The single best expert name from the provided list (e.g., 'Dr. Warren', 'Ruby').")

class Router(dspy.Module):
    def __init__(self, agent_names):
        super().__init__()
        self.expert_roles = "\n".join([f"- {name}: {AGENT_PERSONAS[name]}" for name in agent_names])
        self.route = dspy.Predict(RouteQuestion)

    def forward(self, question, conversation_history):
        prediction = self.route(
            question=question,
            conversation_history=conversation_history,
            expert_roles=self.expert_roles
        )
        return prediction

class Agent(dspy.Module):
    def __init__(self, agent_name: str):
        super().__init__()
        self.agent_name = agent_name
        self.persona = AGENT_PERSONAS[agent_name]
        self.generate_response = dspy.Predict(GenerateResponse)

    def forward(self, context, trigger):
        return self.generate_response(persona=self.persona, context=context, trigger=trigger)

class MemberAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.persona = AGENT_PERSONAS["Rohan"]
        self.generate_question = dspy.Predict(GenerateMemberQuestion)
        self.generate_reply = dspy.Predict(GenerateMemberReply)

    def forward(self, context):
        """Used for initiating new questions."""
        return self.generate_question(persona=self.persona, context=context)
    
    def reply(self, context, last_message):
        """Used for replying to a direct message."""
        return self.generate_reply(persona=self.persona, context=context, last_message=last_message)