"""
Traffic simulation runtime configuration module.

This module handles the setup of the agent runtime environment for the traffic simulation.
It provides a clean interface for initializing the runtime with necessary agent types.
"""

from autogen_core import SingleThreadedAgentRuntime
from traffic_agents import VehicleAssistant, TrafficLightAssistant, PedestrianCrossingAssistant, MyAssistant


async def setup_runtime():
    """
    Initialize and setup the agent runtime for the traffic simulation.
    
    Returns:
        tuple: A tuple containing (runtime, None, None, None) where:
            - runtime: The initialized SingleThreadedAgentRuntime
            - The other None values are placeholders for backward compatibility
    """
    runtime = SingleThreadedAgentRuntime()
    
    # Register the base assistant for core messaging functionality
    await MyAssistant.register(
        runtime, 
        "my_assistant", 
        lambda: MyAssistant("my_assistant")
    )
    
    return runtime, None, None, None
