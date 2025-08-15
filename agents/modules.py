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

class Agent(dspy.Module):
    def __init__(self, agent_name: str):
        super().__init__()
        self.agent_name = agent_name
        self.persona = AGENT_PERSONAS[agent_name]
        self.generate_response = dspy.ChainOfThought(GenerateResponse)

    def forward(self, context, trigger):
        prediction = self.generate_response(
            persona=self.persona,
            context=context,
            trigger=trigger
        )
        return prediction

class MemberAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        # --- CORRECTED LINE ---
        # The persona is now correctly set to only Rohan's persona.
        self.persona = AGENT_PERSONAS["Rohan"]
        self.generate_question = dspy.ChainOfThought(GenerateMemberQuestion)

    def forward(self, context):
        prediction = self.generate_question(
            persona=self.persona,
            context=context
        )
        return prediction