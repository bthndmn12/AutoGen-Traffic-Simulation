import asyncio
import json
import sys
from autogen_core import AgentId
from messages.types import MyMessageType
from runtime import setup_runtime
from vis.simui import (
    TrafficSimulationVisualizer,
    VehicleObject,
    TrafficLightObject,
    PedestrianCrossingObject,
    RoadObject,
    ParkingAreaObject
)
from traffic_agents import (
    VehicleAssistant, 
    TrafficLightAssistant, 
    PedestrianCrossingAssistant,
    ParkingAssistant
)


async def main():
    # Choose config file based on command-line argument
    if len(sys.argv) > 1 and sys.argv[1] == "basic":
        config_file = "basic_map_config.json"
        print("Using basic traffic scenario without parking areas")
    else:
        config_file = "map_config.json"
        print("Using complete traffic scenario with parking areas")
        
    # Load map config
    with open(config_file) as f:
        config = json.load(f)

    raw_roads = config.get("roads", [])
    lights = config.get("traffic_lights", [])
    crossings = config.get("crossings", [])
    parking_areas = config.get("parking_areas", [])

    # Convert roads to tuples with capacity and id information
    road_tuples = []
    for i, r in enumerate(raw_roads):
        road_id = r.get("id", f"road_{i}")
        capacity = r.get("capacity", 2)  # Default capacity of 2 vehicles
        road_tuples.append((r["x1"], r["y1"], r["x2"], r["y2"], capacity, road_id))

    # Setup runtime
    runtime, _, _, _ = await setup_runtime()
    runtime.start()
    await asyncio.sleep(1)

    visualizer = TrafficSimulationVisualizer()

    # Draw roads first
    for r in raw_roads:
        road_capacity = r.get("capacity", 2)
        visualizer.add_object(RoadObject(x1=r["x1"], y1=r["y1"], x2=r["x2"], y2=r["y2"], capacity=road_capacity, road_id=r.get("id")))

    # Register and visualize parking areas (if available)
    parking_agents = []
    for p in parking_areas:
        try:
            await ParkingAssistant.register(
                runtime,
                p["id"],
                lambda name=p["id"], x=p["x"], y=p["y"], capacity=p["capacity"], 
                       parking_time=p.get("parking_time", 2), exit_time=p.get("exit_time", 1):
                    ParkingAssistant(name, x, y, capacity, parking_time, exit_time)
            )
        except ValueError:
            pass  # Agent already exists
            
        agent = await runtime._get_agent(AgentId(p["id"], "default"))
        parking_agents.append((p["id"], agent))
        visualizer.add_object(ParkingAreaObject(
            p["id"], agent, x=p["x"], y=p["y"],
            parking_type=p.get("type", "street")
        ))

    # Register and visualize vehicles
    vehicles = []
    for v in config.get("vehicles", []):
        try:
            await VehicleAssistant.register(
                runtime,
                v["id"],
                lambda name=v["id"], x=v["x"], y=v["y"]: VehicleAssistant(
                    name,
                    current_position=0,
                    start_x=x,
                    start_y=y,
                    roads=road_tuples,
                    crossings=crossings,
                    traffic_lights=lights,
                    parking_areas=parking_areas
                )
            )
        except ValueError:
            pass  # Agent already exists

        agent = await runtime._get_agent(AgentId(v["id"], "default"))
        vehicles.append((v["id"], agent))
        visualizer.add_object(VehicleObject(v["id"], agent, x=v["x"], y=v["y"]))

    # Create a dictionary to track all vehicles in the simulation for collision detection
    vehicle_registry = {}
    for vehicle_id, agent in vehicles:
        vehicle_registry[vehicle_id] = agent
    
    # Register the vehicle_registry with each vehicle
    for vehicle_id, agent in vehicles:
        agent.set_vehicle_registry(vehicle_registry)

    # Register and visualize traffic lights
    for tl in lights:
        try:
            await TrafficLightAssistant.register(runtime, tl["id"], lambda name=tl["id"]: TrafficLightAssistant(name))
        except ValueError:
            pass
        agent = await runtime._get_agent(AgentId(tl["id"], "default"))
        visualizer.add_object(TrafficLightObject(tl["id"], agent, x=tl["x"], y=tl["y"]))

    # Register and visualize crossings
    for c in crossings:
        try:
            await PedestrianCrossingAssistant.register(runtime, c["id"], lambda name=c["id"]: PedestrianCrossingAssistant(name))
        except ValueError:
            pass
        agent = await runtime._get_agent(AgentId(c["id"], "default"))
        visualizer.add_object(PedestrianCrossingObject(c["id"], agent, x=c["x"], y=c["y"]))

    # Launch visualizer
    visualizer_task = asyncio.create_task(visualizer.run())

    # Main simulation loop
    simulation_steps = 50
    for i in range(simulation_steps):
        print(f"Simulation step {i}/{simulation_steps}")
        
        # Every 10 steps, send a park command to the first vehicle, but only if using the parking scenario
        if parking_areas and i > 0 and i % 10 == 0 and vehicles:
            vehicle_id, _ = vehicles[0]
            await runtime.send_message(
                MyMessageType(content="park", source="user"),
                AgentId(vehicle_id, "default")
            )
            print(f"Sent park command to {vehicle_id}")
            
        # Regular movement for all vehicles
        for vehicle_id, _ in vehicles:
            await runtime.send_message(
                MyMessageType(content="move", source="user"),
                AgentId(vehicle_id, "default")
            )
            
        await asyncio.sleep(1)

    await runtime.stop()
    visualizer.stop()
    await visualizer_task


if __name__ == '__main__':
    asyncio.run(main())