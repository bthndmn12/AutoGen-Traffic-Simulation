import asyncio
import tkinter as tk
import random
from dataclasses import dataclass

from autogen_core import AgentId, MessageContext, RoutedAgent, message_handler, SingleThreadedAgentRuntime
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

@dataclass
class MyMessageType:
    content: str
    source: str

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient


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


class Visualizer:
    def __init__(self, runtime, vehicle_agent, traffic_light_agent, crossing_agent, tick_interval=1000):
        self.runtime = runtime
        self.vehicle_agent = vehicle_agent
        self.traffic_light_agent = traffic_light_agent
        self.crossing_agent = crossing_agent
        self.tick_interval = tick_interval
        self.running = True
        self.sim_task = None

        self.root = tk.Tk()
        self.root.title("Traffic Simulation Visualizer")
        self.canvas = tk.Canvas(self.root, width=600, height=400, bg="white")
        self.canvas.pack()
        self.info_label = tk.Label(self.root, text="")
        self.info_label.pack()

        self.canvas.create_text(300, 50, text="Test Drawing", fill="black")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(self.tick_interval, self.tick)

    def on_close(self):
        self.running = False
        if self.sim_task:
            self.sim_task.cancel()
        self.root.destroy()

    async def simulation_step(self):
        if not self.running or self.vehicle_agent is None:
            return
        await self.runtime.send_message(
            MyMessageType(content="move", source="user"),
            AgentId("vehicle", self.vehicle_agent.name)
        )
        await self.runtime.send_message(
            MyMessageType(content="change", source="user"),
            AgentId("traffic_light", self.traffic_light_agent.name)
        )
        await self.runtime.send_message(
            MyMessageType(content="pedestrian", source="user"),
            AgentId("pedestrian_crossing", self.crossing_agent.name)
        )
        await asyncio.sleep(0.1)

    def tick(self):
        if not self.running:
            return
        self.sim_task = asyncio.ensure_future(self.simulation_step())
        self.sim_task.add_done_callback(lambda fut: self.update_visuals())
        self.root.after(self.tick_interval, self.tick)

    def update_visuals(self):
        if not self.running:
            return
        print("Updating visuals...")
        veh_pos = self.vehicle_agent.current_position
        light_state = self.traffic_light_agent.state
        crossing_occupied = self.crossing_agent.is_occupied

        self.canvas.delete("all")
        self.canvas.create_rectangle(50, 200, 550, 250, fill="gray")
        veh_x = 50 + veh_pos * 20
        if veh_x > 550:
            veh_x = 550
        self.draw_vehicle_triangle(veh_x, 225)
        light_color = "green" if light_state.upper() == "GREEN" else "red"
        self.canvas.create_oval(290, 150, 310, 170, fill=light_color)
        cross_color = "orange" if crossing_occupied else "white"
        self.canvas.create_rectangle(320, 200, 340, 250, fill=cross_color)
        self.info_label.config(
            text=f"Vehicle Pos: {veh_pos} | Traffic Light: {light_state} | Crossing: {'occupied' if crossing_occupied else 'free'}"
        )

    def draw_vehicle_triangle(self, x, y):
        size = 10
        points = [x - size, y - size, x - size, y + size, x + size, y]
        self.canvas.create_polygon(points, fill="yellow", outline="black")

    def start(self):
        self.running = True
        self.root.mainloop()

def create_vehicle(name="vehicle_2"):
    agent = VehicleAssistant(name, current_position=0)
    print(f"Created vehicle agent with ID type: {agent.id.type}")
    return agent

def create_traffic_light(name="traffic_light_2"):
    agent = TrafficLightAssistant(name)
    print(f"Created traffic light agent with ID type: {agent.id.type}")
    return agent

def create_crossing(name="pedestrian_crossing_2"):
    agent = PedestrianCrossingAssistant(name)
    print(f"Created pedestrian crossing agent with ID type: {agent.id.type}")
    return agent

async def main():
    runtime = SingleThreadedAgentRuntime()

    vehicle_id_str = "vehicle_2"
    traffic_light_id_str = "traffic_light_2"
    crossing_id_str = "pedestrian_crossing_2"
    
    vehicle_agent = await VehicleAssistant.register(
        runtime, vehicle_id_str, lambda: create_vehicle(vehicle_id_str)
    )
    traffic_light_agent = await TrafficLightAssistant.register(
        runtime, traffic_light_id_str, lambda: create_traffic_light(traffic_light_id_str)
    )
    crossing_agent = await PedestrianCrossingAssistant.register(
        runtime, crossing_id_str, lambda: create_crossing(crossing_id_str)
    )
    
    print(f"Registered vehicle ID: {vehicle_agent}")
    print(f"Registered traffic light ID: {traffic_light_agent}")
    print(f"Registered crossing ID: {crossing_agent}")
    
    vehicle_agent_id = vehicle_agent
    traffic_light_agent_id = traffic_light_agent
    crossing_agent_id = crossing_agent
    
    print("Agents registered successfully")
    
    try:
        agent = await runtime._get_agent(vehicle_agent_id)
        print(f"Successfully got agent: {agent.id}")
    except Exception as e:
        print(f"Could not get agent: {e}")
    
    visualizer = RuntimeVisualizer(
        runtime, 
        vehicle_agent_id, 
        traffic_light_agent_id, 
        crossing_agent_id,
        tick_interval=1000
    )
    
    await visualizer.run()

class RuntimeVisualizer:
    def __init__(self, runtime, vehicle_id, traffic_light_id, crossing_id, tick_interval=1000):
        self.runtime = runtime
        self.vehicle_id = vehicle_id
        self.traffic_light_id = traffic_light_id
        self.crossing_id = crossing_id
        self.tick_interval = tick_interval
        
        self.vehicle_position = 0
        self.vehicle_parked = False
        self.light_state = "RED"
        self.crossing_occupied = False
        
        self.root = tk.Tk()
        self.root.title("Traffic Simulation Visualizer")
        self.canvas = tk.Canvas(self.root, width=600, height=400, bg="white")
        self.canvas.pack()
        self.info_label = tk.Label(self.root, text="")
        self.info_label.pack()
        
        self.running = True
        self.step_count = 0
        self.max_steps = 20
        
    async def run(self):
        self.root.after(500, self.schedule_tick)
        
        while self.running and self.step_count < self.max_steps:
            self.root.update()
            await asyncio.sleep(0.01)
            
        if self.root.winfo_exists():
            self.root.destroy()
            
    def schedule_tick(self):
        if not self.running or self.step_count >= self.max_steps:
            self.running = False
            return
            
        asyncio.ensure_future(self.simulation_step())
        self.root.after(self.tick_interval, self.schedule_tick)
            
    async def simulation_step(self):
        self.step_count += 1
        
        sim_source = AgentId("sim", "simulation")
        
        print(f"Step {self.step_count}/{self.max_steps}: Sending messages to agents...")
        
        try:
            print(f"Sending to vehicle: {self.vehicle_id}")
            
            try:
                await self.runtime.send_message(
                    MyMessageType("move", "sim"), 
                    self.vehicle_id
                )
                await self.runtime.process_messages()
                print("Vehicle message sent successfully")
            except Exception as e:
                print(f"Error sending to vehicle: {e}")
            
            try:
                await self.runtime.send_message(
                    MyMessageType("change", "sim"), 
                    self.traffic_light_id
                )
                await self.runtime.process_messages()
                print("Traffic light message sent successfully")
            except Exception as e:
                print(f"Error sending to traffic light: {e}")
            
            try:
                await self.runtime.send_message(
                    MyMessageType("pedestrian", "sim"), 
                    self.crossing_id
                )
                await self.runtime.process_messages()
                print("Pedestrian crossing message sent successfully")
            except Exception as e:
                print(f"Error sending to pedestrian crossing: {e}")
            
            self.vehicle_position += 1 if not self.vehicle_parked else 0
            self.light_state = "GREEN" if random.random() > 0.5 else "RED"
            self.crossing_occupied = random.random() > 0.7
            
            self.update_visuals()
            
        except Exception as e:
            print(f"Error in simulation step: {e}")
            
    def update_visuals(self):
        self.canvas.delete("all")
        
        self.canvas.create_rectangle(50, 200, 550, 250, fill="gray")
        
        veh_x = 50 + self.vehicle_position * 20
        if veh_x > 550:
            veh_x = 550
        self.draw_vehicle_triangle(veh_x, 225)
        
        light_color = "green" if self.light_state == "GREEN" else "red"
        self.canvas.create_oval(290, 150, 310, 170, fill=light_color)
        
        cross_color = "orange" if self.crossing_occupied else "white"
        self.canvas.create_rectangle(320, 200, 340, 250, fill=cross_color)
        
        self.info_label.config(
            text=f"Step: {self.step_count}/{self.max_steps} | Vehicle Pos: {self.vehicle_position} | " 
                 f"Traffic Light: {self.light_state} | Crossing: {'occupied' if self.crossing_occupied else 'free'}"
        )
        
    def draw_vehicle_triangle(self, x, y):
        size = 10
        points = [x - size, y - size, x - size, y + size, x + size, y]
        self.canvas.create_polygon(points, fill="yellow", outline="black")

if __name__ == "__main__":
    asyncio.run(main())
