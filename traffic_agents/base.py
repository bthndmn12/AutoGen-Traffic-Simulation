from autogen_core import RoutedAgent, AgentId, MessageContext, message_handler
from messages.types import MyMessageType


class MyAssistant(RoutedAgent):
    """Base agent class for all traffic simulation agents
    
    This class serves as the foundation for all specialized traffic agents 
    in the simulation (vehicles, traffic lights, pedestrian crossings, etc.)
    """
    
    def __init__(self, name):
        """Initialize the base agent with a name
        
        Args:
            name (str): Unique identifier for this agent
        """
        super().__init__(name)
        self.name = name

    def _process_road_properties(self):
        """Placeholder for processing road properties"""
        pass

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> None:
        """Default message handler for all derived agents
        
        This method will be overridden by specialized agents.
        
        Args:
            message (MyMessageType): The incoming message
            ctx (MessageContext): Context info for the message
        """
        print(f"{self.id.type} received message: {message.content}")
