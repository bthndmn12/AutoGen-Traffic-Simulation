from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType
import math
import random


def is_nearby(obj1, obj2, threshold=30):
    return abs(obj1[0] - obj2[0]) <= threshold and abs(obj1[1] - obj2[1]) <= threshold

def is_close_to_vehicle(vehicle1_pos, vehicle2_pos, threshold=25):
    """Check if two vehicles are close to each other"""
    x1, y1 = vehicle1_pos
    x2, y2 = vehicle2_pos
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return distance < threshold

def is_intersection(road1, road2):
    """Check if two roads intersect"""
    # Unpack coordinates
    x1, y1, x2, y2 = road1[:4]  # First 4 elements are coordinates
    x3, y3, x4, y4 = road2[:4]
    
    # Check if one road is horizontal and the other is vertical
    road1_horizontal = abs(y2 - y1) < abs(x2 - x1)
    road2_horizontal = abs(y4 - y3) < abs(x4 - x3)
    
    if road1_horizontal == road2_horizontal:
        return False  # Parallel roads don't intersect for our purposes
    
    # Find intersection point
    if road1_horizontal:
        # Road 1 is horizontal, Road 2 is vertical
        horizontal, vertical = road1, road2
    else:
        # Road 1 is vertical, Road 2 is horizontal
        horizontal, vertical = road2, road1
    
    h_x1, h_y1, h_x2, h_y2 = horizontal[:4]
    v_x1, v_y1, v_x2, v_y2 = vertical[:4]
    
    # Check if the vertical road's x is between the horizontal road's x values
    if not (min(h_x1, h_x2) <= v_x1 <= max(h_x1, h_x2)):
        return False
    
    # Check if the horizontal road's y is between the vertical road's y values
    if not (min(v_y1, v_y2) <= h_y1 <= max(v_y1, v_y2)):
        return False
    
    # They intersect
    return (v_x1, h_y1)  # Return intersection point

class VehicleAssistant(MyAssistant):
    def __init__(self, name, current_position=0, start_x=0, start_y=0, roads=None, crossings=None, traffic_lights=None, parking_areas=None):
        super().__init__(name)
        self.x = start_x
        self.y = start_y
        self.current_position = current_position
        self.parked = False
        self.wait_times = []
        self.current_wait = 0
        self.roads = roads or []
        self.crossings = crossings or []
        self.traffic_lights = traffic_lights or []
        self.parking_areas = parking_areas or []
        self.movement_progress = 0.0  # Progress along the current road segment (0.0 to 1.0)
        self.movement_step = 0.1      # How much to move along the road per step
        self.route = [0]              # Start with the first road
        self.next_turn_options = []   # Store possible turns at intersections
        self.is_turning = False
        
        # Vehicle registry for collision detection
        self.vehicle_registry = {}
        
        # Road occupancy tracking
        self.road_occupancy = {}  # Dictionary to track occupancy by road_id
        
        # Parking state
        self.parking_state = "driving"  # driving, searching, parking, parked, exiting
        self.target_parking = None      # Current parking area target
        self.parking_timer = 0          # Timer for parking/exiting process
        self.parking_desire = 0.3       # Probability to seek parking when near a parking area
        
        # Calculate possible turns at each road segment
        self._calculate_possible_turns()

    def set_vehicle_registry(self, registry):
        """Set the vehicle registry for collision detection"""
        self.vehicle_registry = registry

    def _calculate_possible_turns(self):
        """Pre-calculate the possible turns from each road segment"""
        self.turn_options = {}
        
        # For each road, check which other roads it intersects with
        for i, road1 in enumerate(self.roads):
            turns = []
            for j, road2 in enumerate(self.roads):
                if i != j:  # Don't check road against itself
                    intersection = is_intersection(road1, road2)
                    if intersection:
                        # This is a potential turn: road1 -> road2
                        turns.append((j, intersection))
            
            if turns:
                self.turn_options[i] = turns
                
        print(f"{self.name}: Calculated turn options: {self.turn_options}")

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> None:
        print(f"{self.name} (Vehicle) received message: {message.content}")
        response_message = ""

        if "move" in message.content.lower():
            # Handle different vehicle states
            if self.parking_state == "parked":
                # Vehicle is parked, randomly decide if it should exit
                if random.random() < 0.2:  # 20% chance to exit each cycle
                    await self._exit_parking()
                    response_message = f"Initiating exit from parking at {self.target_parking}"
                else:
                    response_message = f"Vehicle is parked at {self.target_parking}"
            
            elif self.parking_state == "parking" or self.parking_state == "exiting":
                # Vehicle is in parking or exiting process
                self.parking_timer -= 1
                if self.parking_timer <= 0:
                    if self.parking_state == "parking":
                        self.parking_state = "parked"
                        response_message = f"Completed parking at {self.target_parking}"
                    else:  # exiting
                        self.parking_state = "driving"
                        self.parked = False
                        self.target_parking = None
                        response_message = f"Completed exiting from parking"
                else:
                    response_message = f"Still {self.parking_state}... {self.parking_timer}s remaining"
            
            elif self.parked:
                response_message = "The vehicle is parked and cannot move."
            
            else:
                # Check for collision with other vehicles before moving
                if await self._check_for_collisions():
                    self.wait_time += 1
                    response_message = f"Cannot move due to potential collision. Wait time: {self.wait_time} sec."
                else:
                    # Decide whether to continue on current road or make a turn
                    if self.is_turning:
                        # Already in turning process, continue the turn
                        response_message = await self._continue_turn()
                    
                    # Check if near a parking area and decide to park
                    elif await self._check_for_parking():
                        response_message = f"Vehicle found parking at {self.target_parking}"
                    
                    elif self.movement_progress >= 0.95 and self.current_position in self.turn_options:
                        # Near the end of the road segment and at a potential turn point
                        self.next_turn_options = self.turn_options[self.current_position]
                        should_turn = random.random() < 0.6  # 60% chance to turn at an intersection
                        
                        if should_turn and self.next_turn_options:
                            # Choose a random turn
                            next_road_idx, intersection_point = random.choice(self.next_turn_options)
                            print(f"{self.name} decided to turn onto road {next_road_idx} at {intersection_point}")
                            
                            # Check if target road has capacity
                            if not await self._check_road_capacity(next_road_idx):
                                self.wait_time += 1
                                response_message = f"Cannot turn onto road {next_road_idx} - at capacity. Wait time: {self.wait_time} sec."
                            else:
                                # Start turning
                                self.is_turning = True
                                self.next_road_idx = next_road_idx
                                self.intersection_point = intersection_point
                                self.movement_progress = 0.0  # Reset progress for the new road
                                response_message = f"Vehicle turning onto road {next_road_idx}"
                        else:
                            # Continue on current road
                            response_message = await self._move_forward()
                    else:
                        # Not near an intersection or decided not to turn
                        response_message = await self._move_forward()

        elif "park" in message.content.lower():
            if not self.parked and self.parking_state == "driving":
                # Find nearest parking
                parking = self._find_nearest_parking()
                if parking:
                    # Request parking
                    self.target_parking = parking["id"]
                    self.parked = True
                    # Here is a bit buggy, it uses a lot of searching
                    self.parking_state = "searching"
                    response_message = f"Searching for parking at {self.target_parking}"
                else:
                    response_message = "No parking areas available"
            else:
                response_message = f"Cannot park now. Current state: {self.parking_state}"
                
        elif "unpark" in message.content.lower() or "exit" in message.content.lower():
            if self.parking_state == "parked":
                await self._exit_parking()
                response_message = f"Initiating exit from parking at {self.target_parking}"
            else:
                response_message = f"Cannot exit parking. Current state: {self.parking_state}"
        else:
            response_message = "Unknown command."

        print(f"{self.name} (Vehicle) responds with: {response_message}")

    async def _check_for_parking(self):
        """Check if vehicle is near a parking area and should try to park"""
        if self.parking_state != "driving" or random.random() > self.parking_desire:
            return False
            
        # Check each parking area to see if we're near it
        for parking in self.parking_areas:
            if is_nearby((self.x, self.y), (parking["x"], parking["y"]), 50):
                # Found a parking area nearby, try to park
                self.target_parking = parking["id"]
                parking_response = await self._request_parking(parking["id"])
                
                if "accepted" in parking_response:
                    # Extract parking time from response
                    try:
                        parking_time = int(parking_response.split("=")[1])
                    except (IndexError, ValueError):
                        parking_time = 3  # Default if parsing fails
                        
                    self.parking_state = "parking"
                    self.parking_timer = parking_time
                    self.parked = True
                    print(f"{self.name}: Starting to park at {parking['id']}, time: {parking_time}s")
                    return True
                else:
                    # Parking rejected, continue driving
                    self.target_parking = None
                    print(f"{self.name}: Parking rejected at {parking['id']}: {parking_response}")
        
        return False

    async def _exit_parking(self):
        """Exit from current parking"""
        if not self.target_parking or self.parking_state != "parked":
            return
            
        exit_response = await self._request_exit(self.target_parking)
        
        if "accepted" in exit_response:
            # Extract exit time from response
            try:
                exit_time = int(exit_response.split("=")[1])
            except (IndexError, ValueError):
                exit_time = 2  # Default if parsing fails
                
            self.parking_state = "exiting"
            self.parking_timer = exit_time
            print(f"{self.name}: Starting to exit from {self.target_parking}, time: {exit_time}s")
        else:
            # Exit rejected
            print(f"{self.name}: Exit rejected from {self.target_parking}: {exit_response}")

    async def _request_parking(self, parking_id):
        """Send a request to park at a parking area"""
        try:
            parking_agent_id = AgentId(parking_id, "default")
            response = await self.runtime.send_message(
                MyMessageType(content="park", source=self.name), 
                parking_agent_id
            )
            return response.content
        except Exception as e:
            print(f"{self.name}: Error requesting parking: {e}")
            return "error"

    async def _request_exit(self, parking_id):
        """Send a request to exit from a parking area"""
        try:
            parking_agent_id = AgentId(parking_id, "default")
            response = await self.runtime.send_message(
                MyMessageType(content="exit", source=self.name), 
                parking_agent_id
            )
            return response.content
        except Exception as e:
            print(f"{self.name}: Error requesting exit: {e}")
            return "error"

    def _find_nearest_parking(self):
        """Find the nearest parking area that isn't full"""
        nearest_parking = None
        min_distance = float('inf')
        
        for parking in self.parking_areas:
            distance = math.sqrt((self.x - parking["x"])**2 + (self.y - parking["y"])**2)
            if distance < min_distance:
                nearest_parking = parking
                min_distance = distance
                
        return nearest_parking

    async def _check_for_collisions(self):
        """Check if there are any other vehicles too close to this one"""
        if not self.vehicle_registry:
            return False
            
        my_position = (self.x, self.y)
        
        for vehicle_id, vehicle in self.vehicle_registry.items():
            # Skip checking against self
            if vehicle_id == self.name:
                continue
                
            other_position = (vehicle.x, vehicle.y)
            if is_close_to_vehicle(my_position, other_position):
                print(f"{self.name}: Potential collision detected with {vehicle_id}")
                return True
                
        return False

    async def _check_road_capacity(self, road_idx):
        """Check if the road has capacity for another vehicle"""
        if road_idx >= len(self.roads):
            return True  # Default to allow if road doesn't exist
            
        road = self.roads[road_idx]
        if len(road) < 5:
            return True  # No capacity information
            
        capacity = road[4]
        road_id = road[5] if len(road) >= 6 else f"road_{road_idx}"
        
        # Count vehicles on this road
        vehicle_count = 0
        for vehicle_id, vehicle in self.vehicle_registry.items():
            if vehicle.current_position == road_idx:
                vehicle_count += 1
                
        print(f"{self.name}: Road {road_id} capacity check: {vehicle_count}/{capacity}")
        return vehicle_count < capacity

    async def _continue_turn(self):
        """Continue the turning process"""
        # Check if we're at an intersection that might have a traffic light or crossing
        if await self._check_for_obstacles(self.intersection_point):
            self.current_wait += 1
            return f"Waiting at intersection due to red light or occupied crossing. Wait time: {self.wait_time}"

        # Check for other vehicles at intersection (collision avoidance)
        if await self._check_for_collisions():
            self.current_wait += 1
            return f"Waiting at intersection due to other vehicles. Wait time: {self.wait_time}"

        # Check if target road has capacity before completing turn
        if not await self._check_road_capacity(self.next_road_idx):
            self.current_wait += 1
            return f"Waiting to turn - target road at capacity. Wait time: {self.wait_time}"

        # Vehicle moves, append the time in the list and reset the counter
        if self.current_wait > 0:
            self.wait_times.append(self.current_wait)
            self.current_wait = 0
        
        # Complete the turn
        self.is_turning = False
        self.current_position = self.next_road_idx
        self.update_coordinates()
        self.route.append(self.current_position)
        
        return f"Vehicle completed turn onto road {self.current_position} at ({self.x:.1f}, {self.y:.1f})"

    async def _move_forward(self):
        """Move forward along the current road"""
        current_xy = (self.x, self.y)
        next_xy = self.get_next_position()
        
        if not next_xy:
            return "No further road segment to follow."
            
        # Check for obstacles like traffic lights or pedestrian crossings
        if await self._check_for_obstacles(current_xy):
            self.current_wait += 1
            return f"Waiting at position {self.current_position} due to red light or occupied crossing. Wait time: {self.current_wait} sec."
            
        # If we're going to advance to the next road segment, check its capacity
        next_road_idx = self.current_position + 1
        if self.movement_progress + self.movement_step >= 1.0:
            if next_road_idx >= len(self.roads):
                next_road_idx = 0  # Loop back to the first road
                
            if not await self._check_road_capacity(next_road_idx):
                self.current_wait += 1
                return f"Cannot advance to next road segment - at capacity. Wait time: {self.current_wait} sec."
        
        # Update position along road
        self.movement_progress += self.movement_step
        
        # If we've reached the end of this road segment
        if self.movement_progress >= 1.0:
            self.current_position = next_road_idx
            self.route.append(self.current_position)
            self.movement_progress = 0.0
            if self.current_wait > 0:
                self.wait_times.append(self.current_wait) 
            self.current_wait = 0
            msg = f"Vehicle moved to road segment {self.current_position}"
        else:
            msg = f"Vehicle moving along road segment {self.current_position} ({self.movement_progress:.1f})"
        
        # Update actual x,y coordinates along the road
        self.update_coordinates()
        return msg

    async def _check_for_obstacles(self, position):
        """Check for traffic lights and pedestrian crossings at the given position"""
        x, y = position
        
        # Check traffic lights
        for light in self.traffic_lights:
            if is_nearby((light["x"], light["y"]), (x, y)):
                light_id = AgentId(light["id"], "default")
                res = await self.runtime.send_message(
                    MyMessageType(content="request_state", source=self.name), 
                    light_id
                )
                if "red" in res.content.lower():
                    print(f"{self.name} stopped at red light {light['id']} at ({light['x']}, {light['y']})")
                    return True

        # Check pedestrian crossings
        for crossing in self.crossings:
            if is_nearby((crossing["x"], crossing["y"]), (x, y)):
                crossing_id = AgentId(crossing["id"], "default")
                res = await self.runtime.send_message(
                    MyMessageType(content="request_state", source=self.name), 
                    crossing_id
                )
                if "occupied" in res.content.lower():
                    print(f"{self.name} stopped at occupied crossing {crossing['id']} at ({crossing['x']}, {crossing['y']})")
                    return True

        return False

    def get_next_position(self):
        """Get the next position the vehicle will move to"""
        if self.is_turning:
            return self.intersection_point
        elif self.current_position + 1 < len(self.roads):
            return self.roads[self.current_position + 1][:2]  # Return start of next segment
        elif len(self.roads) > 0:
            return self.roads[0][:2]  # Loop back to the first road
        return None
        
    def update_coordinates(self):
        """Update the vehicle's coordinates based on current road and progress"""
        if self.is_turning:
            # If we're turning, move toward the intersection point
            current_road = self.roads[self.current_position]
            target_road = self.roads[self.next_road_idx]
            
            # During first half of turn, move to intersection
            if self.movement_progress < 0.5:
                progress_normalized = self.movement_progress * 2  # Scale 0-0.5 to 0-1
                # Move from current position to intersection
                x1, y1 = self.x, self.y
                x2, y2 = self.intersection_point
                self.x = x1 + (x2 - x1) * progress_normalized
                self.y = y1 + (y2 - y1) * progress_normalized
            else:
                # During second half, move from intersection to the new road
                progress_normalized = (self.movement_progress - 0.5) * 2  # Scale 0.5-1 to 0-1
                # Move from intersection to the start of the target road
                x1, y1 = self.intersection_point
                x2, y2 = target_road[:2]  # Start of target road
                self.x = x1 + (x2 - x1) * progress_normalized
                self.y = y1 + (y2 - y1) * progress_normalized
        elif self.current_position < len(self.roads):
            # Regular movement along a road
            road = self.roads[self.current_position]
            x1, y1, x2, y2 = road[:4]  # First 4 elements are coordinates
            
            # Interpolate position along the road based on progress
            self.x = x1 + (x2 - x1) * self.movement_progress
            self.y = y1 + (y2 - y1) * self.movement_progress
        
        print(f"Vehicle {self.name} updated coordinates to ({self.x:.1f}, {self.y:.1f}), progress: {self.movement_progress:.1f}, on road: {self.current_position}")

    async def should_wait(self, next_pos):
        """Legacy method kept for compatibility"""
        return await self._check_for_obstacles(next_pos)
