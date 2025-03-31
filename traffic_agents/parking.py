from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType
import random
import asyncio


class ParkingAssistant(MyAssistant):
    def __init__(self, name, x, y, capacity, parking_time=2, exit_time=1):
        super().__init__(name)
        self.x = x
        self.y = y
        self.capacity = capacity
        self.parking_time = parking_time  # Time it takes to park (in seconds)
        self.exit_time = exit_time        # Time it takes to exit (in seconds)
        self.parked_vehicles = {}         # Dictionary of parked vehicles {vehicle_id: time_remaining}
        self.exiting_vehicles = {}        # Dictionary of vehicles exiting {vehicle_id: time_remaining}
        self.parking_task = asyncio.create_task(self.run_parking_area())
    
    async def run_parking_area(self):
        """Update parking and exiting timers"""
        while True:
            await asyncio.sleep(1)  # Update every second
            
            # Update parking vehicles timers
            to_remove = []
            for vehicle_id, time_remaining in self.parked_vehicles.items():
                if time_remaining > 0:
                    self.parked_vehicles[vehicle_id] = time_remaining - 1
                    print(f"{self.name}: Vehicle {vehicle_id} parking... {time_remaining}s remaining")
                else:
                    # Parking complete
                    to_remove.append(vehicle_id)
                    print(f"{self.name}: Vehicle {vehicle_id} has completed parking")
            
            # Remove vehicles that have completed parking
            for vehicle_id in to_remove:
                self.parked_vehicles.pop(vehicle_id)
            
            # Update exiting vehicles timers
            to_remove = []
            for vehicle_id, time_remaining in self.exiting_vehicles.items():
                if time_remaining > 0:
                    self.exiting_vehicles[vehicle_id] = time_remaining - 1
                    print(f"{self.name}: Vehicle {vehicle_id} exiting... {time_remaining}s remaining")
                else:
                    # Exiting complete
                    to_remove.append(vehicle_id)
                    print(f"{self.name}: Vehicle {vehicle_id} has completed exiting")
            
            # Remove vehicles that have completed exiting
            for vehicle_id in to_remove:
                self.exiting_vehicles.pop(vehicle_id)
    
    @property
    def current_occupancy(self):
        """Get current number of parked vehicles"""
        return len(self.parked_vehicles) + len(self.exiting_vehicles)
    
    @property
    def is_full(self):
        """Check if parking area is at capacity"""
        return self.current_occupancy >= self.capacity
    
    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> MyMessageType:
        print(f"{self.name} (Parking Area) received message: {message.content}")
        
        response_message = "Invalid command received."
        
        if "request_state" in message.content.lower():
            response_message = f"available" if not self.is_full else "full"
        
        elif "park" in message.content.lower():
            vehicle_id = message.source
            
            if self.is_full:
                response_message = f"rejected: parking is full ({self.current_occupancy}/{self.capacity})"
            else:
                # Random variation in parking time
                actual_parking_time = max(1, int(self.parking_time + random.uniform(-0.5, 1.0)))
                self.parked_vehicles[vehicle_id] = actual_parking_time
                response_message = f"accepted: parking_time={actual_parking_time}"
        
        elif "exit" in message.content.lower():
            vehicle_id = message.source
            
            if vehicle_id in self.parked_vehicles:
                # Vehicle is still parking, can't exit yet
                response_message = f"rejected: vehicle is still parking"
            else:
                # Random variation in exit time
                actual_exit_time = max(1, int(self.exit_time + random.uniform(-0.2, 0.5)))
                self.exiting_vehicles[vehicle_id] = actual_exit_time
                response_message = f"accepted: exit_time={actual_exit_time}"
        
        print(f"{self.name} (Parking Area) responds with: {response_message}")
        return MyMessageType(content=response_message, source=self.name)