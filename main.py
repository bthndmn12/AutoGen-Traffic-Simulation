"""
Main entry point for the traffic simulation system.

This module handles configuration loading, agent initialization, visualization,
and the main simulation loop.
"""

import asyncio
import json
import sys
import argparse
import io
import datetime
import os
from contextlib import redirect_stdout
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
    TrafficLightRLAssistant,  # Import the RL traffic light agent 
    PedestrianCrossingAssistant,
    PedestrianCrossingRLAssistant,  # Import the RL pedestrian crossing agent
    ParkingAssistant
)

# Track pedestrian crossing statistics for analysis
crossing_stats = {
    "queue_sizes": {},     # Track queue sizes over time
    "occupation_times": {},  # Track how long crossings are occupied
    "vehicle_waits": {}    # Track how long vehicles wait at each crossing
}


def parse_command_line_args():
    """Parse and return command-line arguments for the simulation"""
    parser = argparse.ArgumentParser(description='Traffic Simulation Parameters')
    parser.add_argument('mode', nargs='?', default='complete', choices=['basic', 'complete'], 
                        help='Simulation mode: basic (no parking) or complete')
    parser.add_argument('--sim-time', type=int, default=50, 
                        help='Total number of seconds/iterations to be simulated')
    parser.add_argument('--lane-capacity', type=int, default=None, 
                        help='Default capacity of each lane (overrides config file)')
    parser.add_argument('--traffic-light-wait', type=int, default=None, 
                        help='Default waiting times for traffic lights (seconds)')
    parser.add_argument('--pedestrian-wait', type=int, default=None, 
                        help='Default waiting times for pedestrian crossings (seconds)')
    parser.add_argument('--parking-time', type=int, default=None, 
                        help='Average parking times for vehicles (seconds)')
    parser.add_argument('--exit-time', type=int, default=None, 
                        help='Average exit times from parking (seconds)')
    parser.add_argument('--parking-capacity', type=int, default=None, 
                        help='Default capacity of parking areas')
    parser.add_argument('--use-rl', action='store_true', 
                        help='Use reinforcement learning agents instead of standard agents')
    parser.add_argument('--epsilon', type=float, default=0.1, 
                        help='Exploration rate for RL agents (epsilon value)')
    parser.add_argument('--learning-rate', type=float, default=0.1, 
                        help='Learning rate for RL agents (alpha value)')
    
    return parser.parse_args()


def load_and_override_config(args):
    """Load configuration file and apply command-line overrides"""
    # Choose config file based on simulation mode
    if args.mode == "basic":
        config_file = "basic_map_config.json"
        print("Using basic traffic scenario without parking areas")
    else:
        config_file = "map_config.json"
        print("Using complete traffic scenario with parking areas")
        
    # Load map config
    with open(config_file) as f:
        config = json.load(f)

    # Apply command-line overrides to config
    if args.lane_capacity:
        print(f"Overriding lane capacity to {args.lane_capacity}")
        for road in config.get("roads", []):
            road["capacity"] = args.lane_capacity
    
    if args.parking_capacity and "parking_areas" in config:
        print(f"Overriding parking capacity to {args.parking_capacity}")
        for parking in config.get("parking_areas", []):
            if parking.get("type") == "building":
                parking["capacity"] = args.parking_capacity * 2
            else:
                parking["capacity"] = args.parking_capacity
            
    if args.parking_time and "parking_areas" in config:
        print(f"Overriding parking time to {args.parking_time}")
        for parking in config.get("parking_areas", []):
            parking["parking_time"] = args.parking_time
            
    if args.exit_time and "parking_areas" in config:
        print(f"Overriding parking exit time to {args.exit_time}")
        for parking in config.get("parking_areas", []):
            parking["exit_time"] = args.exit_time
            
    return config


def prepare_road_tuples(raw_roads):
    """Convert raw road data to enhanced tuples with all properties"""
    road_tuples = []
    
    # First, create a mapping of road IDs for connection resolution
    road_id_map = {}
    for i, r in enumerate(raw_roads):
        road_id = r.get("id", f"road_{i}")
        road_id_map[road_id] = i
    
    # Now process roads with connection resolution
    for i, r in enumerate(raw_roads):
        road_id = r.get("id", f"road_{i}")
        capacity = r.get("capacity", 2)  # Default capacity of 2 vehicles
        one_way = r.get("one_way", False)  # Default is two-way
        is_spawn_point = r.get("is_spawn_point", False)
        is_despawn_point = r.get("is_despawn_point", False)
        
        # Process connections as indices instead of IDs
        connections = []
        if "connections" in r:
            for conn_id in r["connections"]:
                if conn_id in road_id_map:
                    connections.append(road_id_map[conn_id])
                else:
                    print(f"Warning: Road {road_id} has connection to unknown road ID: {conn_id}")
        
        # Create enhanced road tuple with all properties and resolved connections
        road_tuple = (r["x1"], r["y1"], r["x2"], r["y2"], capacity, road_id, 
                      one_way, is_spawn_point, is_despawn_point, connections)
        road_tuples.append(road_tuple)
    
    return road_tuples


async def initialize_visualizer(raw_roads):
    """Create and initialize the traffic simulation visualizer"""
    visualizer = TrafficSimulationVisualizer()

    # Draw roads first
    for r in raw_roads:
        road_capacity = r.get("capacity", 2)
        road_color = r.get("color", "gray")  # Get custom road color if defined
        visualizer.add_object(RoadObject(
            x1=r["x1"], y1=r["y1"], 
            x2=r["x2"], y2=r["y2"], 
            capacity=road_capacity, 
            road_id=r.get("id"),
            color=road_color  # Pass the color to the RoadObject
        ))
    
    return visualizer


async def register_parking_areas(runtime, parking_areas, visualizer, use_rl=False, epsilon=0.1, learning_rate=None):
    """Register and visualize parking area agents"""
    parking_agents = []
    from traffic_agents import ParkingRLAssistant
    for p in parking_areas:
        try:
            if use_rl:
                await ParkingRLAssistant.register(
                    runtime,
                    p["id"],
                    lambda name=p["id"], x=p["x"], y=p["y"], capacity=p["capacity"], \
                           parking_time=p.get("parking_time", 2), exit_time=p.get("exit_time", 1):
                        ParkingRLAssistant(name, x, y, capacity, parking_time, exit_time, epsilon=epsilon, learning_rate=learning_rate)
                )
                print(f"Registered RL Parking Agent: {p['id']}")
            else:
                await ParkingAssistant.register(
                    runtime,
                    p["id"],
                    lambda name=p["id"], x=p["x"], y=p["y"], capacity=p["capacity"], \
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
    return parking_agents


async def register_vehicles(runtime, vehicles_config, road_tuples, crossings, lights, parking_areas, visualizer, spawn_points):
    """Register and visualize vehicle agents"""
    vehicles = []
    
    # Create a mapping of road IDs to their indices in the road_tuples list
    road_id_to_index = {}
    for i, road_tuple in enumerate(road_tuples):
        if len(road_tuple) >= 6:  # Make sure the road has an ID
            road_id = road_tuple[5]
            road_id_to_index[road_id] = i
    
    # Filter out any spawn points that don't match valid road IDs
    valid_spawn_points = []
    for sp in spawn_points:
        if "road_id" in sp and sp["road_id"] in road_id_to_index:
            valid_spawn_points.append(sp)
        else:
            print(f"WARNING: Invalid spawn point {sp.get('id', 'unknown')} references nonexistent road: {sp.get('road_id', 'none')}")
    
    if not valid_spawn_points:
        print("ERROR: No valid spawn points found! Vehicles may spawn at incorrect locations.")
    else:
        print(f"Found {len(valid_spawn_points)} valid spawn points: {[sp['id'] for sp in valid_spawn_points]}")
    
    # Initialize spawn point rotation counter
    spawn_point_index = 0
    
    for v in vehicles_config:
        # Determine the correct spawn point and starting position
        starting_position = 0
        start_x, start_y = v.get("x", 0), v.get("y", 0)
        
        # If this vehicle should use a spawn point and we have valid spawn points
        if v.get("spawn", False) and valid_spawn_points:
            # Use rotation to pick the next spawn point to ensure distribution
            spawn_point = valid_spawn_points[spawn_point_index % len(valid_spawn_points)]
            spawn_point_index += 1
            
            # Set starting coordinates from spawn point
            start_x, start_y = spawn_point["x"], spawn_point["y"]
            
            # Set the starting road position to the corresponding road index
            starting_position = road_id_to_index[spawn_point["road_id"]]
            print(f"Vehicle {v['id']} spawning at {spawn_point['id']} on road {spawn_point['road_id']} (index: {starting_position})")
        else:
            # For non-spawn vehicles, just use their configured position
            print(f"Vehicle {v['id']} using fixed position (x: {start_x}, y: {start_y})")
        
        try:
            await VehicleAssistant.register(
                runtime,
                v["id"],
                lambda name=v["id"], x=start_x, y=start_y, position=starting_position: VehicleAssistant(
                    name,
                    current_position=position,
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
        agent.entered = False
        agent.start_x = start_x
        agent.start_y = start_y
        vehicles.append((v["id"], agent))
        visualizer.add_object(VehicleObject(v["id"], agent, x=start_x, y=start_y))
    
    # Create a registry for collision detection
    vehicle_registry = {vehicle_id: agent for vehicle_id, agent in vehicles}
    
    # Register the vehicle_registry with each vehicle
    for vehicle_id, agent in vehicles:
        agent.set_vehicle_registry(vehicle_registry)
        
    return vehicles


async def register_traffic_lights(runtime, lights, sim_params, visualizer, use_rl=False, epsilon=0.1, learning_rate=None):
    """Register and visualize traffic light agents"""
    for tl in lights:
        try:
            if use_rl:
                # Use RL-based traffic light agent
                await TrafficLightRLAssistant.register(
                    runtime, tl["id"], 
                    lambda name=tl["id"]: TrafficLightRLAssistant(
                        name,
                        epsilon=epsilon,
                        learning_rate=learning_rate
                    )
                )
                print(f"Registered RL Traffic Light Agent: {tl['id']}")
            else:
                # Use standard traffic light agent
                await TrafficLightAssistant.register(
                    runtime, tl["id"], 
                    lambda name=tl["id"]: TrafficLightAssistant(
                        name,
                        change_time=sim_params.get("traffic_light_wait")
                    )
                )
                print(f"Registered Standard Traffic Light Agent: {tl['id']}")
        except ValueError:
            pass  # Agent already exists
            
        agent = await runtime._get_agent(AgentId(tl["id"], "default"))
        visualizer.add_object(TrafficLightObject(tl["id"], agent, x=tl["x"], y=tl["y"]))


async def register_pedestrian_crossings(runtime, crossings, sim_params, visualizer, use_rl=False, epsilon=0.1, learning_rate=None):
    """Register and visualize pedestrian crossing agents"""
    for c in crossings:
        try:
            if use_rl:
                # Use RL-based pedestrian crossing agent
                road_type = c.get("road_type", "2_carriles")  # Default to 2 lanes if not specified
                await PedestrianCrossingRLAssistant.register(
                    runtime, c["id"], 
                    lambda name=c["id"], road_type=road_type: PedestrianCrossingRLAssistant(
                        name,
                        road_type=road_type,
                        epsilon=epsilon,
                        learning_rate=learning_rate
                    )
                )
                print(f"Registered RL Pedestrian Crossing Agent: {c['id']} for {road_type} road")
            else:
                # Use standard pedestrian crossing agent
                await PedestrianCrossingAssistant.register(
                    runtime, c["id"], 
                    lambda name=c["id"]: PedestrianCrossingAssistant(
                        name,
                        wait_time=sim_params.get("pedestrian_wait")
                    )
                )
                print(f"Registered Standard Pedestrian Crossing Agent: {c['id']}")
        except ValueError:
            pass  # Agent already exists
            
        agent = await runtime._get_agent(AgentId(c["id"], "default"))
        visualizer.add_object(PedestrianCrossingObject(c["id"], agent, x=c["x"], y=c["y"]))


async def run_simulation(runtime, vehicles, parking_areas, simulation_steps):
    """Run the main simulation loop for the specified number of steps"""
    for i in range(simulation_steps):
        print(f"Simulation step {i}/{simulation_steps}")

        for idx, (vehicle_id, agent) in enumerate(vehicles):
            if agent.entered:
                continue  # Skip already entered

            if idx == 0 or (vehicles[idx - 1][1].x != vehicles[idx - 1][1].start_x or vehicles[idx - 1][1].y != vehicles[idx - 1][1].start_y):
                agent.entered = True
                print(f"{vehicle_id} has entered the environment.")
                break 
        
        # Every 10 steps, send a park command to the first vehicle, but only if using the parking scenario
        if parking_areas and i > 0 and i % 10 == 0 and vehicles:
            vehicle_id, _ = vehicles[0]
            await runtime.send_message(
                MyMessageType(content="park", source="user"),
                AgentId(vehicle_id, "default")
            )
            print(f"Sent park command to {vehicle_id}")
            
        # Regular movement for all vehicles
        for vehicle_id, agent in vehicles:
            if agent.entered:
                await runtime.send_message(
                    MyMessageType(content="move", source="user"),
                    AgentId(vehicle_id, "default")
                )
                print(f"Vehicle {vehicle_id} moved to coordinates ({agent.x}, {agent.y})")
            
        await asyncio.sleep(1)


async def main():
    """Main entry point for the traffic simulation"""
    # Setup log capture
    log_buffer = io.StringIO()
    original_stdout = sys.stdout
    
    # Initialize statistics tracking
    simulation_stats = {
        "vehicles_entered": 0,
        "vehicles_exited": 0,
        "wait_times": [],
        "start_time": datetime.datetime.now()
    }
    
    try:
        # Redirect stdout to our buffer
        sys.stdout = log_writer = io.StringIO()
        
        # Parse command-line arguments
        args = parse_command_line_args()
        
        # Print information about RL mode
        if args.use_rl:
            print(f"Using Reinforcement Learning agents with epsilon={args.epsilon}, learning_rate={args.learning_rate}")
        
        # Load and override configuration
        config = load_and_override_config(args)

        # Extract simulation components from config
        raw_roads = config.get("roads", [])
        lights = config.get("traffic_lights", [])
        crossings = config.get("crossings", [])
        parking_areas = config.get("parking_areas", [])
        vehicles_config = config.get("vehicles", [])
        spawn_points = config.get("spawn_points", [])

        # Convert roads to enhanced format
        road_tuples = prepare_road_tuples(raw_roads)
        
        # Store simulation parameters for agents
        sim_params = {
            "traffic_light_wait": args.traffic_light_wait,
            "pedestrian_wait": args.pedestrian_wait
        }
            
        # Setup runtime
        runtime, _, _, _ = await setup_runtime()
        runtime.start()
        await asyncio.sleep(1)

        # Initialize visualizer and components
        visualizer = await initialize_visualizer(raw_roads)
        
        # Register all agent types
        parking_agents = await register_parking_areas(runtime, parking_areas, visualizer, use_rl=args.use_rl, epsilon=args.epsilon, learning_rate=args.learning_rate)
        vehicles = await register_vehicles(runtime, vehicles_config, road_tuples, crossings, lights, parking_areas, visualizer, spawn_points)
        
        # Register traffic lights and pedestrian crossings with RL agents if specified
        await register_traffic_lights(
            runtime, lights, sim_params, visualizer, 
            use_rl=args.use_rl, epsilon=args.epsilon, learning_rate=args.learning_rate
        )
        
        await register_pedestrian_crossings(
            runtime, crossings, sim_params, visualizer, 
            use_rl=args.use_rl, epsilon=args.epsilon, learning_rate=args.learning_rate
        )

        # Launch visualizer
        visualizer_task = asyncio.create_task(visualizer.run())

        # Run simulation
        await run_simulation(runtime, vehicles, parking_areas, args.sim_time)
        
        # Additional statistics for RL agents if used
        if args.use_rl:
            print("\n=== Reinforcement Learning Statistics ===")
            for tl in lights:
                try:
                    agent = await runtime._get_agent(AgentId(tl["id"], "default"))
                    if hasattr(agent, 'rl_model'):  # Check if it's an RL agent
                        print(f"{tl['id']} - Q-values: {agent.rl_model.q.tolist()}")
                        print(f"{tl['id']} - Action counts: {agent.rl_model.action_counts.tolist()}")
                        print(f"{tl['id']} - Total steps: {agent.rl_model.steps}")
                except Exception as e:
                    print(f"Error getting stats for {tl['id']}: {e}")
                    
            for c in crossings:
                try:
                    agent = await runtime._get_agent(AgentId(c["id"], "default"))
                    if hasattr(agent, 'rl_model'):  # Check if it's an RL agent
                        print(f"{c['id']} - Q-values: {agent.rl_model.q.tolist()}")
                        print(f"{c['id']} - Action counts: {agent.rl_model.action_counts.tolist()}")
                        print(f"{c['id']} - Total steps: {agent.rl_model.steps}")
                except Exception as e:
                    print(f"Error getting stats for {c['id']}: {e}")

            for p in parking_areas:
                try:
                    agent = await runtime._get_agent(AgentId(p["id"], "default"))
                    if hasattr(agent, 'rl_model'):
                        print(f"{p['id']} - Q-values: {agent.rl_model.q.tolist()}")
                        print(f"{p['id']} - Action counts: {agent.rl_model.action_counts.tolist()}")
                        print(f"{p['id']} - Total steps: {agent.rl_model.steps}")
                except Exception as e:
                    print(f"Error getting stats for {p['id']}: {e}")
            
            print("=======================================\n")


        # Collect final statistics from vehicles
        print("\n=== Simulation Statistics ===")
        all_wait_times = []
        for vehicle_id, agent in vehicles:
            if agent.entered:
                simulation_stats["vehicles_entered"] += 1
                # Check if vehicle has exited the simulation (despawned)
                if not hasattr(agent, 'x') or agent.x is None:
                    simulation_stats["vehicles_exited"] += 1
                
                # Collect wait times from vehicles
                if hasattr(agent, 'wait_times') and agent.wait_times:
                    simulation_stats["wait_times"].extend(agent.wait_times)
                    all_wait_times.extend(agent.wait_times)
                    # Print sum of wait times instead of the full list
                    total_wait = sum(agent.wait_times)
                    avg_wait = total_wait / len(agent.wait_times) if agent.wait_times else 0
                    print(f"{vehicle_id} - Total wait time: {total_wait} seconds, Waits: {len(agent.wait_times)}, Avg: {avg_wait:.2f} sec/wait")
        
        # Calculate wait time statistics
        if all_wait_times:
            max_wait = max(all_wait_times)
            min_wait = min(all_wait_times)
            avg_wait = sum(all_wait_times) / len(all_wait_times)
            total_wait_time = sum(all_wait_times)
            print(f"\nWait Time Statistics:")
            print(f"  Maximum wait time: {max_wait} seconds")
            print(f"  Minimum wait time: {min_wait} seconds")
            print(f"  Average wait time: {avg_wait:.2f} seconds")
            print(f"  Total wait time (all vehicles): {total_wait_time} seconds")
            print(f"  Total number of waits: {len(all_wait_times)}")
        else:
            print("No wait times recorded in this simulation.")
            
        print("\n=== Detailed Wait Time per Vehicle ===")
        for vehicle_id, agent in vehicles:
            if agent.wait_times:
                max_wait_time = max(agent.wait_times)
                min_wait_time = min(agent.wait_times)
                avg_wait_time = sum(agent.wait_times) / len(agent.wait_times)

                print(f"\nVehicle ID: {vehicle_id}")
                print(f"  Max Wait Time: {max_wait_time} sec")
                print(f"  Min Wait Time: {min_wait_time} sec")
                print(f"  Average Wait Time: {avg_wait_time:.2f} sec")
            else:
                print(f"\nVehicle ID: {vehicle_id} has no wait times recorded.")
            
        print(f"\nVehicles that entered the system: {simulation_stats['vehicles_entered']}")
        print(f"Vehicles that exited the system: {simulation_stats['vehicles_exited']}")
        
        # Calculate total simulation time
        simulation_end_time = datetime.datetime.now()
        simulation_duration = (simulation_end_time - simulation_stats["start_time"]).total_seconds()
        print(f"Total simulation time: {simulation_duration:.2f} seconds")
        print("===========================\n")

        # Cleanup
        await runtime.stop()
        visualizer.stop()
        await visualizer_task
        
        # Save log file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"simulation_log_{timestamp}.txt"
        
        with open(log_filename, "w", encoding="utf-8") as log_file:
            log_file.write(log_writer.getvalue())
            
        print(f"\nSimulation logs saved to {log_filename}", file=original_stdout)
        
    finally:
        # Restore original stdout
        sys.stdout = original_stdout


if __name__ == '__main__':
    asyncio.run(main())