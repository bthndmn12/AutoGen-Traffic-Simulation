from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType
import random
import asyncio
from rl.parking import ParkingRL


class ParkingAssistant(MyAssistant):
    """Parking area agent that manages vehicle parking and exiting"""
    
    def __init__(self, name, x, y, capacity, parking_time=2, exit_time=1):
        super().__init__(name)
        # Location and capacity properties
        self.x = x
        self.y = y
        self.capacity = capacity
        
        # Timing parameters
        self.parking_time = parking_time  # Default time to park (seconds)
        self.exit_time = exit_time        # Default time to exit (seconds)
        
        # Vehicle tracking collections
        self.parked_vehicles = {}         # Vehicles in parking process {vehicle_id: time_remaining}
        self.exiting_vehicles = {}        # Vehicles in exit process {vehicle_id: time_remaining}
        self.parked_durations = {}        # Vehicles currently parked {vehicle_id: duration}
        
        # Start background task for parking management
        self.parking_task = asyncio.create_task(self.run_parking_area())
    
    async def run_parking_area(self):
        """Background task to update parking timers and manage vehicles"""
        while True:
            await asyncio.sleep(1)  # Update every second
            
            # Process vehicles that are parking
            await self._update_parking_vehicles()
            
            # Process parked vehicles and send exit notifications
            await self._check_parked_vehicles()
            
            # Process vehicles that are exiting
            await self._update_exiting_vehicles()
    
    async def _update_parking_vehicles(self):
        """Update timers for vehicles in the parking process"""
        to_remove = []
        
        for vehicle_id, time_remaining in self.parked_vehicles.items():
            if time_remaining > 0:
                self.parked_vehicles[vehicle_id] = time_remaining - 1
                print(f"{self.name}: Vehicle {vehicle_id} parking... {time_remaining}s remaining")
            else:
                # Parking complete
                to_remove.append(vehicle_id)
                self.parked_durations[vehicle_id] = 0
                print(f"{self.name}: Vehicle {vehicle_id} has completed parking")
        
        # Remove vehicles that finished parking
        for vehicle_id in to_remove:
            self.parked_vehicles.pop(vehicle_id)
    
    async def _check_parked_vehicles(self):
        """Check parked vehicles and notify them to exit when needed"""
        exit_notifications = []
        
        for vehicle_id, duration in list(self.parked_durations.items()):
            # Increment time parked
            self.parked_durations[vehicle_id] = duration + 1
            
            # Determine if vehicle should exit:
            # - Either after long duration (15 seconds)
            # - Or randomly after a minimum duration (5 seconds)
            if duration > 15 or (duration > 5 and random.random() < 0.15):
                exit_notifications.append(vehicle_id)
                del self.parked_durations[vehicle_id]
        
        # Send exit notifications
        for vehicle_id in exit_notifications:
            try:
                vehicle_agent_id = AgentId(vehicle_id, "default")
                await self.runtime.send_message(
                    MyMessageType(content=f"exit_notification", source=self.name),
                    vehicle_agent_id
                )
                print(f"{self.name}: Notified vehicle {vehicle_id} to exit parking")
            except Exception as e:
                print(f"{self.name}: Error sending exit notification to {vehicle_id}: {e}")
    
    async def _update_exiting_vehicles(self):
        """Update timers for vehicles in the exit process"""
        to_remove = []
        
        for vehicle_id, time_remaining in self.exiting_vehicles.items():
            if time_remaining > 0:
                self.exiting_vehicles[vehicle_id] = time_remaining - 1
                print(f"{self.name}: Vehicle {vehicle_id} exiting... {time_remaining}s remaining")
            else:
                # Exit complete
                to_remove.append(vehicle_id)
                print(f"{self.name}: Vehicle {vehicle_id} has completed exiting")
        
        # Remove vehicles that finished exiting
        for vehicle_id in to_remove:
            self.exiting_vehicles.pop(vehicle_id)
    
    @property
    def current_occupancy(self):
        """Get current number of vehicles in the parking area"""
        return len(self.parked_vehicles) + len(self.exiting_vehicles) + len(self.parked_durations)
    
    @property
    def is_full(self):
        """Check if parking area is at capacity"""
        return self.current_occupancy >= self.capacity
    
    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> MyMessageType:
        """Handle incoming messages to the parking area"""
        print(f"{self.name} (Parking Area) received message: {message.content}")
        
        response_message = "Invalid command received."
        vehicle_id = message.source
        
        if "request_state" in message.content.lower():
            response_message = f"available" if not self.is_full else "full"
        
        elif "park" in message.content.lower():
            if self.is_full:
                response_message = f"rejected: parking is full ({self.current_occupancy}/{self.capacity})"
            else:
                # Add slight variation to parking time
                actual_parking_time = max(1, int(self.parking_time + random.uniform(-0.5, 1.0)))
                self.parked_vehicles[vehicle_id] = actual_parking_time
                response_message = f"accepted: parking_time={actual_parking_time}"
        
        elif "exit" in message.content.lower():
            if vehicle_id in self.parked_vehicles:
                # Vehicle is still parking, can't exit yet
                response_message = f"rejected: vehicle is still parking"
            else:
                # Remove from parked tracking if present
                if vehicle_id in self.parked_durations:
                    del self.parked_durations[vehicle_id]
                
                # Add slight variation to exit time
                actual_exit_time = max(1, int(self.exit_time + random.uniform(-0.2, 0.5)))
                self.exiting_vehicles[vehicle_id] = actual_exit_time
                response_message = f"accepted: exit_time={actual_exit_time}"
        
        print(f"{self.name} (Parking Area) responds with: {response_message}")
        return MyMessageType(content=response_message, source=self.name)


class ParkingRLAssistant(MyAssistant):
    """Parking area agent that uses reinforcement learning to manage parking and exits"""
    def __init__(self, name, x, y, capacity, parking_time=2, exit_time=1, epsilon=0.1, learning_rate=None):
        super().__init__(name)
        self.x = x
        self.y = y
        self.capacity = capacity
        self.parking_time = parking_time
        self.exit_time = exit_time
        self.epsilon = epsilon
        self.learning_rate = learning_rate
        self.rl_model = ParkingRL(alfa=self.learning_rate)
        self.parked_vehicles = {}
        self.exiting_vehicles = {}
        self.parked_durations = {}
        self.rl_task = asyncio.create_task(self.run_parking_rl())

    async def run_parking_rl(self):
        while True:
            await asyncio.sleep(1)
            for vehicle_id in list(self.parked_durations.keys()):
                occupancy = self.current_occupancy
                duration = self.parked_durations[vehicle_id]
                reward, action = self.rl_model.step(occupancy, self.capacity)
                # RL
                if action == 1:
                    self.parked_durations.pop(vehicle_id)
                    self.exiting_vehicles[vehicle_id] = self.exit_time
                    print(f"{self.name} RL: Vehicle {vehicle_id} decided to exit (RL or forced)")
                    try:
                        vehicle_agent_id = AgentId(vehicle_id, "default")
                        await self.runtime.send_message(
                            MyMessageType(content=f"exit_notification", source=self.name),
                            vehicle_agent_id
                        )
                        print(f"{self.name}: Notified vehicle {vehicle_id} to exit parking (RL)")
                    except Exception as e:
                        print(f"{self.name}: Error sending exit notification to {vehicle_id}: {e}")
                else:
                    self.parked_durations[vehicle_id] += 1
            await self._update_parking_vehicles()
            await self._update_exiting_vehicles()

    async def _update_parking_vehicles(self):
        to_remove = []
        for vehicle_id, time_remaining in self.parked_vehicles.items():
            if time_remaining > 0:
                self.parked_vehicles[vehicle_id] = time_remaining - 1
                print(f"{self.name}: Vehicle {vehicle_id} parking... {time_remaining}s remaining (RL)")
            else:
                to_remove.append(vehicle_id)
                self.parked_durations[vehicle_id] = 0
                print(f"{self.name}: Vehicle {vehicle_id} has completed parking (RL)")
        for vehicle_id in to_remove:
            self.parked_vehicles.pop(vehicle_id)

    async def _update_exiting_vehicles(self):
        to_remove = []
        for vehicle_id, time_remaining in self.exiting_vehicles.items():
            if time_remaining > 0:
                self.exiting_vehicles[vehicle_id] = time_remaining - 1
                print(f"{self.name}: Vehicle {vehicle_id} exiting... {time_remaining}s remaining (RL)")
            else:
                to_remove.append(vehicle_id)
                print(f"{self.name}: Vehicle {vehicle_id} has completed exiting (RL)")
        for vehicle_id in to_remove:
            self.exiting_vehicles.pop(vehicle_id)

    def update_epsilon(self, new_epsilon):
        if 0 <= new_epsilon <= 1:
            self.epsilon = new_epsilon
            print(f"{self.name} RL epsilon updated to {self.epsilon}")
            return True
        return False

    def update_learning_rate(self, new_rate):
        if 0 < new_rate <= 1:
            self.learning_rate = new_rate
            self.rl_model.alfa = new_rate
            print(f"{self.name} RL learning rate updated to {self.learning_rate}")
            return True
        return False

    @property
    def current_occupancy(self):
        return len(self.parked_vehicles) + len(self.exiting_vehicles) + len(self.parked_durations)

    @property
    def is_full(self):
        return self.current_occupancy >= self.capacity

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> MyMessageType:
        print(f"{self.name} (RL Parking Area) received message: {message.content}")
        response_message = "Invalid command received."
        vehicle_id = message.source
        if "request_state" in message.content.lower():
            response_message = f"available" if not self.is_full else "full"
        elif "park" in message.content.lower():
            if self.is_full:
                response_message = f"rejected: parking is full ({self.current_occupancy}/{self.capacity})"
            else:
                actual_parking_time = max(1, int(self.parking_time + random.uniform(-0.5, 1.0)))
                self.parked_vehicles[vehicle_id] = actual_parking_time
                response_message = f"accepted: parking_time={actual_parking_time}"
        elif "exit" in message.content.lower():
            if vehicle_id in self.parked_vehicles:
                response_message = f"rejected: vehicle is still parking"
            else:
                if vehicle_id in self.parked_durations:
                    del self.parked_durations[vehicle_id]
                actual_exit_time = max(1, int(self.exit_time + random.uniform(-0.2, 0.5)))
                self.exiting_vehicles[vehicle_id] = actual_exit_time
                response_message = f"accepted: exit_time={actual_exit_time}"
        elif "update_epsilon" in message.content.lower():
            try:
                new_epsilon = float(message.content.split("=")[1])
                success = self.update_epsilon(new_epsilon)
                response_message = f"Epsilon updated to {new_epsilon}" if success else "Invalid epsilon value"
            except (IndexError, ValueError):
                response_message = "Invalid epsilon parameter"
        elif "update_learning" in message.content.lower():
            try:
                new_rate = float(message.content.split("=")[1])
                success = self.update_learning_rate(new_rate)
                response_message = f"Learning rate updated to {new_rate}" if success else "Invalid learning rate value"
            except (IndexError, ValueError):
                response_message = "Invalid learning rate parameter"
        elif "request_rl_stats" in message.content.lower():
            response_message = (f"Steps: {self.rl_model.steps}, "
                               f"Q-values: {self.rl_model.q.tolist()}, "
                               f"Epsilon: {self.epsilon}")
        print(f"{self.name} (RL Parking Area) responds with: {response_message}")
        return MyMessageType(content=response_message, source=self.name)
