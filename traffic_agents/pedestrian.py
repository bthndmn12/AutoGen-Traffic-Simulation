import asyncio
import random
from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType
from collections import deque
from rl.pedestrian import PedestrianCrossingRL


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


class PedestrianCrossingRLAssistant(MyAssistant):
    """Pedestrian crossing agent that uses reinforcement learning to control pedestrian flow"""
    
    def __init__(self, name, road_type="2_carriles", epsilon=0.1, learning_rate=None):
        super().__init__(name)
        
        # Crossing state
        self.is_occupied = False
        self.road_type = road_type  # Indicates the type of road (1 or 2 lanes)
        
        # RL parameters
        self.epsilon = epsilon
        self.learning_rate = learning_rate
        
        # Initialize the RL model
        self.rl_model = PedestrianCrossingRL(alfa=self.learning_rate)
        
        # Pedestrian tracking
        self.pedestrian_queue = deque()  # Queue of pedestrians waiting to cross
        self.max_queue_length = 0        # Track maximum queue length for statistics
        
        # Start the background task that manages pedestrian activity with RL
        self.crossing_task = asyncio.create_task(self.run_pedestrian_crossing_rl())
    
    async def run_pedestrian_crossing_rl(self):
        """Background task to run the RL-based pedestrian crossing"""
        while True:
            # Simulate new pedestrians arriving
            await self._add_new_pedestrians()
            
            # Use RL to decide when to allow crossing
            await self._make_rl_decision()
            
            # Wait before next decision
            await asyncio.sleep(random.uniform(1.0, 2.0))
    
    async def _add_new_pedestrians(self):
        """Simulate new pedestrians arriving at the crossing"""
        # 30% chance of new pedestrian(s) arriving
        if random.random() < 0.3:
            num_pedestrians = random.randint(1, 3)  # 1-3 pedestrians arrive
            
            for _ in range(num_pedestrians):
                # Each pedestrian takes 1-3 seconds to cross
                self.pedestrian_queue.append(random.randint(1, 3))
            
            # Update statistics
            self.max_queue_length = max(self.max_queue_length, len(self.pedestrian_queue))
            print(f"{self.name}: {num_pedestrians} pedestrians arrived. Queue now: {len(self.pedestrian_queue)}")
    
    async def _make_rl_decision(self):
        """Use the RL model to decide when to allow pedestrians to cross"""
        # Get the current queue length
        queue_length = len(self.pedestrian_queue)
        
        # Make an RL decision
        reward, action = self.rl_model.step(queue_length, self.road_type)
        
        # Action 0: pedestrian crossing is occupied (stop vehicles)
        # Action 1: pedestrian crossing is free (allow vehicles)
        old_state = "occupied" if self.is_occupied else "free"
        if action == 0 and not self.is_occupied and queue_length > 0:
            # Allow pedestrians to cross
            self.is_occupied = True
            pedestrian_time = self.pedestrian_queue.popleft()  # First pedestrian crosses
            
            # Allow more pedestrians to cross if waiting
            while len(self.pedestrian_queue) > 0 and random.random() < 0.7:
                self.pedestrian_queue.popleft()  # Additional pedestrians cross together
                
            print(f"{self.name} RL Pedestrian Crossing is now occupied (stopping traffic). "
                  f"Queue: {len(self.pedestrian_queue)}")
                  
            # Automatically free the crossing after a short time
            await asyncio.sleep(pedestrian_time)
            self.is_occupied = False
            print(f"{self.name} RL Pedestrian Crossing is now free. "
                  f"Queue remaining: {len(self.pedestrian_queue)}")
                  
        elif action == 1 and self.is_occupied:
            # Stop pedestrian crossing
            self.is_occupied = False
            print(f"{self.name} RL Pedestrian Crossing is now free (allowing traffic).")
            
        # Log the decision
        new_state = "occupied" if self.is_occupied else "free"
        print(f"{self.name} RL decision: action={action}, reward={reward}, old_state={old_state}, "
              f"new_state={new_state}, queue={queue_length}")

    def update_epsilon(self, new_epsilon):
        """Update the exploration rate for the RL algorithm"""
        if 0 <= new_epsilon <= 1:
            self.epsilon = new_epsilon
            print(f"{self.name} exploration rate updated to {self.epsilon}")
            return True
        return False
    
    def update_learning_rate(self, new_rate):
        """Update the learning rate for the RL algorithm"""
        if 0 < new_rate <= 1:
            self.learning_rate = new_rate
            self.rl_model.alfa = new_rate
            print(f"{self.name} learning rate updated to {self.learning_rate}")
            return True
        return False
    
    def set_road_type(self, road_type):
        """Set the road type for this crossing"""
        if road_type in ["1_carril", "2_carriles"]:
            self.road_type = road_type
            print(f"{self.name} road type set to {self.road_type}")
            return True
        return False

    @property
    def queue_length(self):
        """Return the current queue length"""
        return len(self.pedestrian_queue)

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> MyMessageType:
        """Handle incoming messages to the pedestrian crossing"""
        print(f"{self.name} (RL Pedestrian Crossing) received message: {message.content}")
        
        if "request_state" in message.content.lower():
            # Include queue length in the response
            response_message = (f"occupied queue={self.queue_length}" if self.is_occupied 
                               else f"free queue={self.queue_length}")
        elif "update_epsilon" in message.content.lower():
            # Extract epsilon parameter
            try:
                new_epsilon = float(message.content.split("=")[1])
                success = self.update_epsilon(new_epsilon)
                response_message = f"Epsilon updated to {new_epsilon}" if success else "Invalid epsilon value"
            except (IndexError, ValueError):
                response_message = "Invalid epsilon parameter"
        elif "update_learning" in message.content.lower():
            # Extract learning rate parameter
            try:
                new_rate = float(message.content.split("=")[1])
                success = self.update_learning_rate(new_rate)
                response_message = f"Learning rate updated to {new_rate}" if success else "Invalid learning rate value"
            except (IndexError, ValueError):
                response_message = "Invalid learning rate parameter"
        elif "set_road_type" in message.content.lower():
            # Extract road type parameter
            try:
                road_type = message.content.split("=")[1].strip()
                success = self.set_road_type(road_type)
                response_message = f"Road type set to {road_type}" if success else "Invalid road type"
            except (IndexError, ValueError):
                response_message = "Invalid road type parameter"
        elif "request_rl_stats" in message.content.lower():
            # Return RL statistics
            response_message = (f"Steps: {self.rl_model.steps}, "
                               f"Q-values: {self.rl_model.q.tolist()}, "
                               f"Epsilon: {self.epsilon}")
        else:
            response_message = "Invalid command received."

        print(f"{self.name} (RL Pedestrian Crossing) responds with: {response_message}")
        return MyMessageType(content=response_message, source=self.name)
