import asyncio
import random
from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType


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


