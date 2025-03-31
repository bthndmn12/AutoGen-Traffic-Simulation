from autogen_core import AgentId, MessageContext, message_handler
from messages.types import MyMessageType

from autogen_core import RoutedAgent

class MyAssistant(RoutedAgent):
    def __init__(self, name):
        super().__init__(name)
        self.name = name

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> None:
        print(f"{self.id.type} received message: {message.content}")
