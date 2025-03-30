import asyncio
import tkinter as tk
import random
from dataclasses import dataclass

from autogen_core import AgentId, MessageContext, RoutedAgent, message_handler, SingleThreadedAgentRuntime
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
import asyncio
import tkinter as tk
import threading
import queue
import traceback
import time
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

AGENT_TYPE = "traffic_sim" 

@dataclass
class MyMessageType:
    content: str
    source: str

class MyAssistant(RoutedAgent):
    def __init__(self, name):
        super().__init__(name)
        self.name = name

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> None:
        print(f"{self.id.type} received message: {message.content}")

class VehicleAssistant(MyAssistant):
    def __init__(self, name, current_position=0):
        super().__init__(name)
        self.name = name
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
                    MyMessageType(content="request_state", source = self.name), traffic_light_id
                )

                traffic_light_state = traffic_light_response.content.lower()

                if "RED" in traffic_light_state:
                    self.wait_time += 1
                    response_message = f"Traffic light is RED. The vehicle waits. Wait time: {self.wait_time} sec."
                    print(f"{self.name} (Vehicle) responds with: {response_message}")
                    return

                pedestrian_response = await self.runtime.send_message(
                    MyMessageType(content="request_state", source = self.name), pedestrian_id
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

class TrafficLightAssistant(MyAssistant):
    def __init__(self, name):
        super().__init__(name)
        self.state = "RED"
        self.change_time = random.randint(1, 2)
        self.time_counter = 0
        self.traffic_light_task = asyncio.create_task(self.run_traffic_light())

    async def run_traffic_light(self):
      print("Comenzando traffic light")
      while True:
        await asyncio.sleep(self.change_time)
        self.state = "GREEN" if self.state == "RED" else "RED"
        print(f"{self.name} changed to {self.state}")
        self.time_counter = 0

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> MyMessageType:
        print(f"{self.name}  (Traffic Light) received message: {message.content}")

        if "request_state" in message.content.lower():
            print(f"{self.name}  responding with state: {self.state}")
            response_message = self.state

        else:
          response_message = "Invalid command received"

        print(f"{self.name} responds with: {response_message}")
        response = MyMessageType(content=response_message, source="user")

        return response


class PedestrianCrossingAssistant(MyAssistant):
    def __init__(self, name):
        super().__init__(name)
        self.is_occupied = False
        self.occupancy_time = 0
        self.occupancy_counter = 0
        self.crossing_task = asyncio.create_task(self.run_pedestrian_crossing())

    async def run_pedestrian_crossing(self):
      print("Comenzado asincrono pedestrian crossing")
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
        response = MyMessageType(content=response_message, source=self.name)

        return response


async def run_traffic_simulation():

    runtime = SingleThreadedAgentRuntime()
    
    await MyAssistant.register(runtime, "my_asistant", lambda: MyAssistant("my_asistant"))
    await VehicleAssistant.register(runtime, "vehicle_1", lambda: VehicleAssistant("vehicle_1"))
    await TrafficLightAssistant.register(runtime, "traffic_light_1", lambda: TrafficLightAssistant("traffic_light_1"))
    await PedestrianCrossingAssistant.register(runtime, "pedestrian_crossing_1", lambda: PedestrianCrossingAssistant("pedestrian_crossing_1"))

    runtime.start()

    for _ in range(20):
        await runtime.send_message(MyMessageType(content="move", source="user"), AgentId("vehicle_1", "default"))
        await asyncio.sleep(2)

    await runtime.stop()



vehicle_instance = None
traffic_light_instance = None
pedestrian_instance = None

def create_vehicle():
    global vehicle_instance
    vehicle_instance = VehicleAssistant("vehicle_1")
    return vehicle_instance

def create_traffic_light():
    global traffic_light_instance
    traffic_light_instance = TrafficLightAssistant("traffic_light_1")
    return traffic_light_instance

def create_pedestrian():
    global pedestrian_instance
    pedestrian_instance = PedestrianCrossingAssistant("pedestrian_crossing_1")
    return pedestrian_instance

# --- New Visualization Integration Code ---
class TrafficSimulationVisualizer:
    def __init__(self):
        self.running = True
        self.root = tk.Tk()
        self.root.title("Traffic Simulation Visualizer")
        self.canvas = tk.Canvas(self.root, width=600, height=400, bg="white")
        self.canvas.pack()
        self.info_label = tk.Label(self.root, text="")
        self.info_label.pack()

    async def run(self):
        while self.running:
            self.update_canvas()
            self.root.update()
            await asyncio.sleep(0.1)
        self.root.destroy()

    def update_canvas(self):
        self.canvas.delete("all")
        # Draw road
        self.canvas.create_rectangle(50, 200, 550, 250, fill="gray")
        # Draw vehicle (if available) based on its current_position
        veh_x = 50 + (vehicle_instance.current_position * 20 if vehicle_instance else 0)
        veh_x = min(veh_x, 550)
        self.canvas.create_rectangle(veh_x - 10, 220, veh_x + 10, 240, fill="blue")
        # Draw traffic light based on its state (if available)
        light_state = traffic_light_instance.state if traffic_light_instance else "RED"
        light_color = "green" if light_state.upper() == "GREEN" else "red"
        self.canvas.create_oval(300, 150, 320, 170, fill=light_color)
        # Draw pedestrian crossing based on occupancy
        crossing_color = "orange" if (pedestrian_instance and pedestrian_instance.is_occupied) else "white"
        self.canvas.create_rectangle(320, 200, 340, 250, fill=crossing_color)
        # Update info label
        veh_pos = vehicle_instance.current_position if vehicle_instance else 0
        crossing_status = "occupied" if (pedestrian_instance and pedestrian_instance.is_occupied) else "free"
        self.info_label.config(
            text=f"Vehicle Pos: {veh_pos} | Traffic Light: {light_state} | Crossing: {crossing_status}"
        )

    def stop(self):
        self.running = False

# --- Combined Main Function ---
async def main():
    runtime = SingleThreadedAgentRuntime()
    
    # Register agents using our helper functions to capture instances
    await MyAssistant.register(runtime, "my_asistant", lambda: MyAssistant("my_asistant"))
    await VehicleAssistant.register(runtime, "vehicle_1", create_vehicle)
    await TrafficLightAssistant.register(runtime, "traffic_light_1", create_traffic_light)
    await PedestrianCrossingAssistant.register(runtime, "pedestrian_crossing_1", create_pedestrian)
    
    runtime.start()
    
    # Give agents time to initialize
    await asyncio.sleep(1)
    
    visualizer = TrafficSimulationVisualizer()
    visualizer_task = asyncio.create_task(visualizer.run())
    
    # Run the simulation loop concurrently with visualization
    for _ in range(30):
        await runtime.send_message(MyMessageType(content="move", source="user"), AgentId("vehicle_1", "default"))
        await asyncio.sleep(1)
    
    await runtime.stop()
    visualizer.stop()
    await visualizer_task

if __name__ == '__main__':
    asyncio.run(main())