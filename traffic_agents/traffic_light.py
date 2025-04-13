import asyncio
import random
from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType
from rl.traffic_lihgt import TrafficlightRL  # Import the RL model


class TrafficLightAssistant(MyAssistant):
    """Traffic light agent that coordinates with other traffic lights in groups"""
    
    # Class variables for group coordination
    light_groups = {
        "north_south": [],  # Vertical roads
        "east_west": []     # Horizontal roads
    }
    
    group_states = {
        "north_south": "RED",
        "east_west": "GREEN"
    }
    
    coordination_initialized = False

    def __init__(self, name, change_time=None, group=None):
        super().__init__(name)
        
        # Auto-determine light group based on name
        if group is None:
            if "left" in name.lower() or "right" in name.lower():
                self.group = "north_south"  # Vertical roads
            elif "top" in name.lower() or "bottom" in name.lower():
                self.group = "east_west"    # Horizontal roads
            elif "mid" in name.lower():
                # Check if it's vertical or horizontal
                if "left" in name.lower() or "right" in name.lower():
                    self.group = "north_south"
                else:
                    self.group = "east_west"
            else:
                # Default to a group based on ID number
                light_id = int(name.split('_')[-1]) if '_' in name and name.split('_')[-1].isdigit() else 0
                self.group = "north_south" if light_id % 2 == 0 else "east_west"
        else:
            self.group = group
            
        # Register this light to its group
        TrafficLightAssistant.light_groups[self.group].append(name)
        
        # Set initial state based on group
        self.state = TrafficLightAssistant.group_states[self.group]
        
        # Set change time with slight variation
        base_time = change_time if change_time is not None else random.randint(2, 4)
        self.change_time = base_time + random.uniform(-0.5, 0.5)
        
        # Initialize group coordination if this is the first light
        if not TrafficLightAssistant.coordination_initialized:
            self.traffic_light_task = asyncio.create_task(self.coordinate_traffic_lights())

            
            TrafficLightAssistant.coordination_initialized = True
        else:
            self.traffic_light_task = None

    async def coordinate_traffic_lights(self):
        """Centralized coordination of all traffic lights by group"""
        while True:
            # Wait for the change time
            await asyncio.sleep(self.change_time)
            
            # Update all lights in each group
            for group, state in TrafficLightAssistant.group_states.items():
                for light_name in TrafficLightAssistant.light_groups[group]:
                    try:
                        light = await self.runtime._get_agent(AgentId(light_name, "default"))
                        if light:
                            light.state = state
                            print(f"{light_name} changed to {state}")
                    except Exception as e:
                        print(f"Error updating light {light_name}: {e}")
            
            # Swap states for opposing groups
            TrafficLightAssistant.group_states["north_south"] = "GREEN" if TrafficLightAssistant.group_states["north_south"] == "RED" else "RED"
            TrafficLightAssistant.group_states["east_west"] = "GREEN" if TrafficLightAssistant.group_states["east_west"] == "RED" else "RED"

    def update_change_time(self, new_time):
        """Update the traffic light timing"""
        if new_time and new_time > 0:
            self.change_time = new_time
            print(f"{self.name} change time updated to {self.change_time} seconds")
            return True
        return False

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> MyMessageType:
        """Handle incoming messages to the traffic light"""
        print(f"{self.name} (Traffic Light) received message: {message.content}")
        
        if "request_state" in message.content.lower():
            response_message = self.state
        elif "update_timing" in message.content.lower():
            # Extract timing parameter from message
            try:
                new_time = int(message.content.split("=")[1])
                success = self.update_change_time(new_time)
                response_message = f"Timing updated to {new_time}" if success else "Invalid timing value"
            except (IndexError, ValueError):
                response_message = "Invalid timing parameter"
        elif "request_group" in message.content.lower():
            response_message = f"Group: {self.group}, State: {self.state}"
        else:
            response_message = "Invalid command received"

        print(f"{self.name} responds with: {response_message}")
        return MyMessageType(content=response_message, source="user")


class TrafficLightRLAssistant(MyAssistant):
    """Traffic light agent that uses reinforcement learning to control traffic flow"""
    
    # Class variables for statistics and coordination
    light_groups = {
        "north_south": [],  # Vertical roads
        "east_west": []     # Horizontal roads
    }
    
    def __init__(self, name, group=None, epsilon=0.1, learning_rate=None):
        super().__init__(name)
        
        # Auto-determine light group based on name, same as original
        if group is None:
            if "left" in name.lower() or "right" in name.lower():
                self.group = "north_south"  # Vertical roads
            elif "top" in name.lower() or "bottom" in name.lower():
                self.group = "east_west"    # Horizontal roads
            elif "mid" in name.lower():
                # Check if it's vertical or horizontal
                if "left" in name.lower() or "right" in name.lower():
                    self.group = "north_south"
                else:
                    self.group = "east_west"
            else:
                # Default to a group based on ID number
                light_id = int(name.split('_')[-1]) if '_' in name and name.split('_')[-1].isdigit() else 0
                self.group = "north_south" if light_id % 2 == 0 else "east_west"
        else:
            self.group = group
            
        # Register this light to its group
        TrafficLightRLAssistant.light_groups[self.group].append(name)
        
        # Initialize state and RL parameters
        self.state = "RED"  # Initial state
        self.epsilon = epsilon  # Exploration rate
        self.learning_rate = learning_rate  # Learning rate (alpha)
        
        # Initialize the RL model
        self.rl_model = TrafficlightRL(alfa=self.learning_rate)
        
        # Traffic flow monitoring
        self.queue_length = 0  # Number of vehicles waiting at this light
        
        # Start the RL decision task
        self.traffic_light_task = asyncio.create_task(self.run_traffic_light_rl())
    
    async def run_traffic_light_rl(self):
        """Background task to run the RL decision process"""
        while True:
            # Simulate traffic conditions (in a real system, this would come from sensors)
            self.queue_length = self.simulate_queue_length()
            
            # Use RL to make a decision
            reward, action = self.rl_model.step(self, self.queue_length)
            
            # Log the decision and reward
            print(f"{self.name} RL decision: action={action}, reward={reward}, state={self.state}, queue={self.queue_length}")
            
            # Wait before next decision
            await asyncio.sleep(random.uniform(1.5, 2.5))
    
    def simulate_queue_length(self):
        """Simulate traffic queue length based on current state and time of day"""
        # Base queue length depends on light state
        base_queue = random.randint(0, 3) if self.state == "GREEN" else random.randint(1, 8)
        
        # Add some randomness to simulate traffic patterns
        queue = max(0, base_queue + random.randint(-2, 2))
        return queue
    
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

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> MyMessageType:
        """Handle incoming messages to the traffic light"""
        print(f"{self.name} (RL Traffic Light) received message: {message.content}")
        
        if "request_state" in message.content.lower():
            response_message = f"{self.state} queue={self.queue_length}"
        elif "update_epsilon" in message.content.lower():
            # Extract epsilon parameter from message
            try:
                new_epsilon = float(message.content.split("=")[1])
                success = self.update_epsilon(new_epsilon)
                response_message = f"Epsilon updated to {new_epsilon}" if success else "Invalid epsilon value"
            except (IndexError, ValueError):
                response_message = "Invalid epsilon parameter"
        elif "update_learning" in message.content.lower():
            # Extract learning rate parameter from message
            try:
                new_rate = float(message.content.split("=")[1])
                success = self.update_learning_rate(new_rate)
                response_message = f"Learning rate updated to {new_rate}" if success else "Invalid learning rate value"
            except (IndexError, ValueError):
                response_message = "Invalid learning rate parameter"
        elif "request_group" in message.content.lower():
            response_message = f"Group: {self.group}, State: {self.state}"
        elif "request_rl_stats" in message.content.lower():
            # Return RL statistics
            response_message = (f"Steps: {self.rl_model.steps}, "
                               f"Q-values: {self.rl_model.q.tolist()}, "
                               f"Epsilon: {self.epsilon}")
        else:
            response_message = "Invalid command received"

        print(f"{self.name} responds with: {response_message}")
        return MyMessageType(content=response_message, source="user")


