import asyncio
from typing import Optional
from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType


class VehicleAssistant(MyAssistant):
    def __init__(self, name, current_position=0):
        super().__init__(name)
        self.current_position = current_position
        self.parked = False
        self.wait_time = 0

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> None:
        print(f"{self.name} (Vehicle) received message: {message.content}")
        response_message = ""

        if "move" in message.content.lower():
            if self.parked:
                response_message = "The vehicle is parked and cannot move."
            else:
                traffic_light_id = AgentId("traffic_light_1", "default")
                pedestrian_id = AgentId("pedestrian_crossing_1", "default")

                traffic_light_response = await self.runtime.send_message(
                    MyMessageType(content="request_state", source=self.name), traffic_light_id
                )

                traffic_light_state = traffic_light_response.content.lower()

                if "red" in traffic_light_state:
                    self.wait_time += 1
                    response_message = f"Traffic light is RED. The vehicle waits. Wait time: {self.wait_time} sec."
                    print(f"{self.name} (Vehicle) responds with: {response_message}")
                    return

                pedestrian_response = await self.runtime.send_message(
                    MyMessageType(content="request_state", source=self.name), pedestrian_id
                )
                pedestrian_state = pedestrian_response.content.lower()
                print(f"[{self.name}] received pedestrian crossing state: {pedestrian_state}")

                if "occupied" in pedestrian_state:
                    self.wait_time += 1
                    response_message = f"Pedestrian Crossing is occupied. Vehicle waits. Wait time: {self.wait_time} sec."
                    print(f"{self.name} (Vehicle) responds with: {response_message}")
                    return

                self.current_position += 1
                response_message = f"The vehicle moved to position {self.current_position}."
                self.wait_time = 0

        elif "park" in message.content.lower():
            self.parked = True
            response_message = "The vehicle is parked."
        elif "unpark" in message.content.lower():
            self.parked = False
            response_message = "The vehicle is unparked."
        else:
            response_message = "The vehicle is not moving."

        print(f"{self.name} (Vehicle) responds with: {response_message}")
