import asyncio
import random
from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType
from collections import deque


class PedestrianCrossingAssistant(MyAssistant):
    """Pedestrian crossing agent that simulates pedestrians using a crosswalk"""
    
    def __init__(self, name, wait_time=None):
        super().__init__(name)
        # Crossing state
        self.is_occupied = False
        self.occupancy_time = 0
        self.occupancy_counter = 0
        self.wait_time = wait_time
        
        # Pedestrian tracking
        self.pedestrian_queue = deque()  # Queue of pedestrians waiting to cross
        self.max_queue_length = 0        # Track maximum queue length for statistics
        
        # Start the background task that manages pedestrian activity
        self.crossing_task = asyncio.create_task(self.run_pedestrian_crossing())

    async def run_pedestrian_crossing(self):
        """Background task to simulate pedestrian activity at the crossing"""
        while True:
            await asyncio.sleep(random.randint(1, 2))
            
            # Simulate new pedestrians arriving at the crossing
            await self._add_new_pedestrians()
            
            # Process pedestrian crossing state
            await self._update_crossing_state()
    
    async def _add_new_pedestrians(self):
        """Simulate new pedestrians arriving at the crossing"""
        # 40% chance of new pedestrian(s) arriving
        if random.random() < 0.4:
            num_pedestrians = random.randint(1, 3)  # 1-3 pedestrians arrive
            
            for _ in range(num_pedestrians):
                # Each pedestrian takes 1-3 seconds to cross
                self.pedestrian_queue.append(random.randint(1, 3))
            
            # Update statistics
            self.max_queue_length = max(self.max_queue_length, len(self.pedestrian_queue))
            print(f"{self.name}: {num_pedestrians} pedestrians arrived. Queue now: {len(self.pedestrian_queue)}")
    
    async def _update_crossing_state(self):
        """Update the state of the pedestrian crossing"""
        if not self.is_occupied and self.pedestrian_queue:
            # Start a new pedestrian crossing
            self.is_occupied = True
            self.occupancy_time = self.pedestrian_queue.popleft()
            
            # Use configured wait time if provided
            if self.wait_time is not None:
                self.occupancy_time = self.wait_time
                
            self.occupancy_counter = 0
            print(f"{self.name} Pedestrian Crossing is now occupied for {self.occupancy_time} seconds. "
                  f"Queue: {len(self.pedestrian_queue)}")
                  
        elif self.is_occupied:
            # Update ongoing crossing
            self.occupancy_counter += 1
            if self.occupancy_counter >= self.occupancy_time:
                # Crossing completed
                self.is_occupied = False
                print(f"{self.name} Pedestrian Crossing is now free. "
                      f"Queue remaining: {len(self.pedestrian_queue)}")

    def update_wait_time(self, new_time):
        """Update the pedestrian crossing wait time"""
        if new_time and new_time > 0:
            self.wait_time = new_time
            print(f"{self.name} wait time updated to {self.wait_time} seconds")
            return True
        return False

    @property
    def queue_length(self):
        """Return the current queue length"""
        return len(self.pedestrian_queue)

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> MyMessageType:
        """Handle incoming messages to the pedestrian crossing"""
        print(f"{self.name} (Pedestrian Crossing) received message: {message.content}")
        
        if "request_state" in message.content.lower():
            # Include queue length in the response
            response_message = (f"occupied queue={self.queue_length}" if self.is_occupied 
                               else f"free queue={self.queue_length}")
                               
        elif "update_timing" in message.content.lower():
            # Handle crossing time update request
            try:
                new_time = int(message.content.split("=")[1])
                success = self.update_wait_time(new_time)
                response_message = f"Wait time updated to {new_time}" if success else "Invalid wait time value"
            except (IndexError, ValueError):
                response_message = "Invalid timing parameter"
                
        else:
            response_message = "Invalid command received."

        print(f"{self.name} (Pedestrian Crossing) responds with: {response_message}")
        return MyMessageType(content=response_message, source=self.name)
