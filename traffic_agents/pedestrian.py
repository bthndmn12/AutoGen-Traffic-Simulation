import asyncio
import random
from typing import Optional
from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType


class PedestrianCrossingAssistant(MyAssistant):
    def __init__(self, name):
        super().__init__(name)
        self.is_occupied = False
        self.occupancy_time = 0
        self.occupancy_counter = 0
        self.crossing_task = asyncio.create_task(self.run_pedestrian_crossing())

    async def run_pedestrian_crossing(self):
        while True:
            await asyncio.sleep(random.randint(1, 2))
            if not self.is_occupied:
                self.is_occupied = True
                self.occupancy_time = random.randint(1, 3)
                self.occupancy_counter = 0
                print(f"{self.name} Pedestrian Crossing is now occupied for {self.occupancy_time} seconds.")
            else:
                self.occupancy_counter += 1
                if self.occupancy_counter >= self.occupancy_time:
                    self.is_occupied = False
                    print(f"{self.name} Pedestrian Crossing is now free after {self.occupancy_time} seconds.")

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> MyMessageType:
        print(f"{self.name} (Pedestrian Crossing) received message: {message.content}")

        if "request_state" in message.content.lower():
            response_message = "occupied" if self.is_occupied else "free"
        else:
            response_message = "Invalid command received."

        print(f"{self.name} (Pedestrian Crossing) responds with: {response_message}")
        return MyMessageType(content=response_message, source=self.name)
