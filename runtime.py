from autogen_core import SingleThreadedAgentRuntime
from traffic_agents import VehicleAssistant, TrafficLightAssistant, PedestrianCrossingAssistant, MyAssistant

# You no longer need hardcoded instances with dynamic config loading

async def setup_runtime():
    runtime = SingleThreadedAgentRuntime()
    await MyAssistant.register(runtime, "my_assistant", lambda: MyAssistant("my_assistant"))
    return runtime, None, None, None


# from autogen_core import SingleThreadedAgentRuntime
# from traffic_agents import VehicleAssistant, TrafficLightAssistant, PedestrianCrossingAssistant, MyAssistant

# vehicle_instance = None
# traffic_light_instance = None
# pedestrian_instance = None


# def create_vehicle():
#     global vehicle_instance
#     vehicle_instance = VehicleAssistant("vehicle_1")
#     return vehicle_instance


# def create_traffic_light():
#     global traffic_light_instance
#     traffic_light_instance = TrafficLightAssistant("traffic_light_1")
#     return traffic_light_instance


# def create_pedestrian():
#     global pedestrian_instance
#     pedestrian_instance = PedestrianCrossingAssistant("pedestrian_crossing_1")
#     return pedestrian_instance


# async def setup_runtime():
#     runtime = SingleThreadedAgentRuntime()
#     await MyAssistant.register(runtime, "my_assistant", lambda: MyAssistant("my_assistant"))
#     await VehicleAssistant.register(runtime, "vehicle_1", create_vehicle)
#     await TrafficLightAssistant.register(runtime, "traffic_light_1", create_traffic_light)
#     await PedestrianCrossingAssistant.register(runtime, "pedestrian_crossing_1", create_pedestrian)
#     return runtime, vehicle_instance, traffic_light_instance, pedestrian_instance
