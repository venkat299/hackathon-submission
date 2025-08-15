import dspy
from config import AGENT_PERSONAS

class GenerateResponse(dspy.Signature):
    """
    Given a persona, context, and a trigger, generate a conversational, in-character response.
    The response should include a message for the user and, if necessary, a specific action for the simulation to execute.
    """
    persona = dspy.InputField(desc="The persona description for the agent.")
    context = dspy.InputField(desc="The current simulation state, critical events, and recent conversation history.")
    trigger = dspy.InputField(desc="The specific event, data point, or message to respond to.")
    
    response = dspy.OutputField(
        desc="A JSON object containing the response message and an optional action.",
        prefix='{"message": "',
        json_schema={
            "message": "A natural, in-character WhatsApp-style message for the user. IMPORTANT: The message must be concise, between 5 and 50 words.",
            "action": {
                "type": "The type of action to take (e.g., 'INITIATE_SICK_DAY_PROTOCOL', 'FLAG_FOR_EXPERT', 'UPDATE_NARRATIVE_FLAG'). Can be 'NONE'.",
                "payload": "A dictionary with data for the action (e.g., {'expert_name': 'Dr. Warren'}, {'flag': 'consultation_scheduled', 'value': true})."
            }
        }
    )

class GenerateMemberQuestion(dspy.Signature):
    """Given the member's persona and context, generate a relevant, in-character question or comment."""
    persona = dspy.InputField(desc="The persona description for the member.")
    context = dspy.InputField(desc="The current simulation state and recent conversation history.")
    question = dspy.OutputField(desc="A concise, in-character question or statement for the Elyx team. IMPORTANT: The question must be brief, between 5 and 50 words.")


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

    def forward(self, context):
        return self.generate_question(persona=self.persona, context=context)