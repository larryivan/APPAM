import os
from typing import Generator, List, Dict, Optional
from ..agents.react_agent import ReActAgent

class AIService:
    """
    A simplified service to interact with the ReAct Agent.
    This service initializes the agent and acts as a facade for its functionality.
    """

    def __init__(self):
        """Initializes the AI service and the ReAct agent."""
        self.agent = ReActAgent()
        self.last_agent = None
        # The model is now managed by the agent
        self.model = self.agent.model

    def get_react_response(self, message: str, project_id: Optional[str] = None, conversation_history: List[Dict] = None, tool_context: Optional[Dict] = None) -> Generator[str, None, None]:
        """
        Gets a ReAct response from the agent.
        
        Note: Conversation history is not yet implemented in the new agent.
        """
        # The new agent manages its own conversation history internally for now.
        # A more sophisticated history management will be added later.
        if conversation_history:
            # You can yield a message here to inform about the current limitation
            yield "[INFO] Conversation history is not fully supported in the new agent yet, starting a new session.\n"

        # Store the agent instance for later access
        self.last_agent = self.agent
        yield from self.agent.run(user_message=message, project_id=project_id, tool_context=tool_context)

    def get_streaming_response(self, message: str, project_id: Optional[str] = None, conversation_history: List[Dict] = None) -> Generator[str, None, None]:
        """
        Provides a direct streaming response. For now, this will also use the ReAct agent,
        as non-ReAct flows are not the priority in the new architecture.
        """
        # In the new architecture, all interactions are preferred to go through the ReAct agent
        # to ensure tool usage and reasoning. A separate non-ReAct flow can be added if needed.
        yield from self.get_react_response(message, project_id, conversation_history)

    def get_last_agent(self) -> Optional[ReActAgent]:
        """Returns the last agent instance used."""
        return self.last_agent

# Instantiate a global AI service
ai_service = AIService()