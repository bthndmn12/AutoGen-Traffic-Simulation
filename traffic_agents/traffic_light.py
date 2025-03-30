import asyncio
import random
from typing import Optional
from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType


class TrafficLightAssistant(MyAssistant):
    def __init__(self, name):
        super().__init__(name)
        self.state = "RED"
        self.change_time = random.randint(1, 2)
        self.traffic_light_task = asyncio.create_task(self.run_traffic_light())

    async def run_traffic_light(self):
        while True:
            await asyncio.sleep(self.change_time)
            self.state = "GREEN" if self.state == "RED" else "RED"
            print(f"{self.name} changed to {self.state}")

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> MyMessageType:
        print(f"{self.name} (Traffic Light) received message: {message.content}")

        if "request_state" in message.content.lower():
            response_message = self.state
        else:
            response_message = "Invalid command received"

        print(f"{self.name} responds with: {response_message}")
        return MyMessageType(content=response_message, source="user")