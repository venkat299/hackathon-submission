import dspy
from config import AGENT_PERSONAS

class GenerateResponse(dspy.Signature):
    """Given a persona, context, and a trigger, generate a conversational, in-character response."""
    persona = dspy.InputField(desc="The persona description for the agent.")
    context = dspy.InputField(desc="The current simulation state and recent conversation history.")
    trigger = dspy.InputField(desc="The specific event or message to respond to.")
    response = dspy.OutputField(desc="A natural, in-character WhatsApp-style message. Should be concise.")

class GenerateMemberQuestion(dspy.Signature):
    """Given the member's persona and context, generate a relevant, in-character question or comment."""
    persona = dspy.InputField(desc="The persona description for the member.")
    context = dspy.InputField(desc="The current simulation state and recent conversation history.")
    question = dspy.OutputField(desc="A concise, in-character question or statement for the Elyx team.")

class RouteQuestion(dspy.Signature):
    """Given a user's question, recent conversation, and a list of expert roles, choose the best expert to respond."""
    question = dspy.InputField(desc="The user's most recent question.")
    # Add conversation history to the signature
    conversation_history = dspy.InputField(desc="The last few messages in the conversation.")
    expert_roles = dspy.InputField(desc="A detailed list of available experts and their specific roles.")
    expert_name = dspy.OutputField(desc="The single best expert name from the provided list (e.g., 'Dr. Warren', 'Ruby').")

# And update the Router module to pass this new information
class Router(dspy.Module):
    def __init__(self, agent_names):
        super().__init__()
        self.expert_roles = "\n".join([f"- {name}: {AGENT_PERSONAS[name]}" for name in agent_names])
        self.route = dspy.Predict(RouteQuestion)

    def forward(self, question, conversation_history):
        prediction = self.route(
            question=question,
            conversation_history=conversation_history, # Pass the history
            expert_roles=self.expert_roles
        )
        return prediction
    
class Agent(dspy.Module):
    def __init__(self, agent_name: str):
        super().__init__()
        self.agent_name = agent_name
        self.persona = AGENT_PERSONAS[agent_name]
        self.generate_response = dspy.ChainOfThought(GenerateResponse)

    def forward(self, context, trigger):
        return self.generate_response(persona=self.persona, context=context, trigger=trigger)

class MemberAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.persona = AGENT_PERSONAS["Rohan"]
        self.generate_question = dspy.ChainOfThought(GenerateMemberQuestion)

    def forward(self, context):
        return self.generate_question(persona=self.persona, context=context)