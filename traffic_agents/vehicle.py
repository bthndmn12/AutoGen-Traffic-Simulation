from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType
import math
import random


def is_nearby(pos1, pos2, threshold=30):
    """Check if two positions are within a threshold distance of each other using Euclidean distance"""
    x1, y1 = pos1
    x2, y2 = pos2
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return distance < threshold  


def is_close_to_vehicle(pos1, pos2, threshold=15):
    """Check if two vehicles are close to each other using Euclidean distance"""
    x1, y1 = pos1
    x2, y2 = pos2
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return distance < threshold  


def is_intersection(road1, road2):
    """Determine if and where two roads intersect"""
    # Unpack coordinates
    x1, y1, x2, y2 = road1[:4]  # First 4 elements are coordinates
    x3, y3, x4, y4 = road2[:4]
    
    # Check if roads have different orientations
    road1_horizontal = abs(y2 - y1) < abs(x2 - x1)
    road2_horizontal = abs(y4 - y3) < abs(x4 - x3)
    
    if road1_horizontal == road2_horizontal:
        return False  # Parallel roads don't intersect for our purposes
    
    # Find intersection point
    if road1_horizontal:
        horizontal, vertical = road1, road2
    else:
        horizontal, vertical = road2, road1
    
    h_x1, h_y1, h_x2, h_y2 = horizontal[:4]
    v_x1, v_y1, v_x2, v_y2 = vertical[:4]
    
    # Ensure proper order for horizontal road (left to right)
    if h_x1 > h_x2:
        h_x1, h_y1, h_x2, h_y2 = h_x2, h_y2, h_x1, h_y1
    
    # Ensure proper order for vertical road (top to bottom)
    if v_y1 > v_y2:
        v_x1, v_y1, v_x2, v_y2 = v_x2, v_y2, v_x1, v_y1
    
    # Check for valid intersection
    if not (h_x1 <= v_x1 <= h_x2):
        return False
    
    if not (v_y1 <= h_y1 <= v_y2):
        return False
    
    # Return intersection point with exact coordinates
    intersection = get_exact_intersection_point(road1, road2)
    return intersection is not None  


def get_exact_intersection_point(road1, road2):
    """Calculate the exact intersection point of two roads based on their geometry.
    Returns None if roads are parallel or don't intersect."""
    # Extract coordinates
    x1, y1, x2, y2 = road1[:4]
    x3, y3, x4, y4 = road2[:4]
    
    # Check if both roads are vertical or both horizontal (parallel)
    road1_vertical = abs(x2 - x1) < 10  # Consider roads with small x difference as vertical
    road2_vertical = abs(x4 - x3) < 10
    
    if road1_vertical and road2_vertical:
        return None  # Parallel vertical roads
    
    road1_horizontal = abs(y2 - y1) < 10  # Consider roads with small y difference as horizontal
    road2_horizontal = abs(y4 - y3) < 10
    
    if road1_horizontal and road2_horizontal:
        return None  # Parallel horizontal roads
    
    # For a vertical and horizontal road, the intersection is simple
    if road1_vertical and road2_horizontal:
        # Check if they actually intersect
        if min(y1, y2) <= y3 <= max(y1, y2) and min(x3, x4) <= x1 <= max(x3, x4):
            return (x1, y3)
        return None
    
    if road1_horizontal and road2_vertical:
        # Check if they actually intersect
        if min(x1, x2) <= x3 <= max(x1, x2) and min(y3, y4) <= y1 <= max(y3, y4):
            return (x3, y1)
        return None
    
    # General case: neither road is perfectly horizontal or vertical
    # Calculate line equations for both roads: y = mx + b
    try:
        m1 = (y2 - y1) / (x2 - x1)
        b1 = y1 - m1 * x1
        
        m2 = (y4 - y3) / (x4 - x3)
        b2 = y3 - m2 * x3
        
        # If slopes are the same, lines are parallel
        if abs(m1 - m2) < 0.001:
            return None
        
        # Calculate intersection point
        x_intersect = (b2 - b1) / (m1 - m2)
        y_intersect = m1 * x_intersect + b1
        
        # Check if intersection point is on both line segments
        on_road1 = (min(x1, x2) <= x_intersect <= max(x1, x2)) and (min(y1, y2) <= y_intersect <= max(y1, y2))
        on_road2 = (min(x3, x4) <= x_intersect <= max(x3, x4)) and (min(y3, y4) <= y_intersect <= max(y3, y4))
        
        if on_road1 and on_road2:
            return (x_intersect, y_intersect)
        return None
        
    except ZeroDivisionError:
        # Handle case where one of the lines is vertical
        return None  


class VehicleAssistant(MyAssistant):
    """Vehicle agent that handles movement, parking, and interactions with other traffic elements"""
    
    def __init__(self, name, current_position=0, start_x=0, start_y=0, roads=None, crossings=None, traffic_lights=None, parking_areas=None):
        super().__init__(name)
        # Position and movement properties
        self.x = start_x
        self.y = start_y
        self.current_position = current_position
        self.movement_progress = 0.0  # Progress along current road (0.0 to 1.0)
        self.movement_step = 0.05      # Movement increment per step
        self.route = [current_position]  # History of visited road indices
        
        # Environment elements
        self.roads = roads or []
        self.crossings = crossings or []
        self.traffic_lights = traffic_lights or []
        self.parking_areas = parking_areas or []
        
        # Ensure coordinates match the starting road position
        if current_position < len(self.roads):
            # Only adjust if we need to match road coordinates
            road = self.roads[current_position]
            x1, y1 = road[0], road[1]
            
            # If the start position coordinates were not specified (0,0), place at road start
            if start_x == 0 and start_y == 0:
                self.x = x1
                self.y = y1
            # Otherwise, assume the start_x and start_y are correct  
        
        # Print debug information
        print(f"{self.name}: Initialized at position ({self.x}, {self.y}) on road index {current_position}")
        if current_position < len(self.roads) and len(self.roads[current_position]) >= 6:
            print(f"{self.name}: Starting on road {self.roads[current_position][5]}")
        
        # Turning properties
        self.next_turn_options = []   # Available turns at current position
        self.is_turning = False
        self.turn_options = {}        # All possible turns indexed by road position
        
        # Road system properties
        self.road_connections = {}    # Valid connections between roads
        self.one_way_roads = set()    # Indices of one-way roads
        self.spawn_points = {}        # Where vehicles can enter the simulation
        self.despawn_points = {}      # Where vehicles can exit the simulation
        self.vehicle_registry = {}    # Registry of all vehicles for collision detection
        self.road_occupancy = {}      # Track road occupancy by id
        
        # Waiting/timing properties
        self.wait_times = []          # History of waiting durations
        self.current_wait = 0         # Current waiting time
        
        # Parking properties
        self.parked = False
        self.parking_state = "driving"  # States: driving, parking, parked, exiting
        self.target_parking = None      # Current parking target
        self.parking_timer = 0          # Countdown for parking/exiting
        self.parking_desire = 0.3       # Probability to park when near parking
        self.parking_cooldown = 0       # Cooldown before attempting to park again
        self.recent_parkings = []       # Recently used parking areas to avoid immediate re-entry
        
        
        # Initialize road system and turn options
        # these 3 mfs killed the simulation
        self._process_road_properties()
        # self._validate_spawn_point()  
        # self._calculate_possible_turns()  

    def _validate_spawn_point(self):
        """Ensure the vehicle spawns at a valid point on the road."""
        if self.current_position < len(self.roads):
            road = self.roads[self.current_position]
            if len(road) >= 4:
                x1, y1, x2, y2 = road[:4]
                self.x = x1
                self.y = y1
                print(f"{self.name}: Spawned at valid point ({self.x}, {self.y}) on road {self.current_position}")
            else:
                print(f"{self.name}: Invalid road data for spawning.")
        else:
            print(f"{self.name}: Invalid road index for spawning.")  

    def _calculate_turns_at_intersections(self):
        """Enhance turn logic to handle intersections with crossings and traffic lights."""
        key_intersections = [
            {"x": 250, "y": 50,  "crossings": ["crossing_top_2",    "crossing_top_3"]},
            {"x": 250, "y": 250, "crossings": ["crossing_mid_2",    "crossing_mid_3"]},
            {"x": 250, "y": 450, "crossings": ["crossing_bottom_2", "crossing_bottom_3"]},
            {
                "x": 50,  "y": 250, 
                "crossings": ["crossing_left_mid"], 
                "traffic_lights": ["traffic_light_left_top", "traffic_light_left_bottom"]
            },
            {
                "x": 450, "y": 250, 
                "crossings": ["crossing_right_mid"], 
                "traffic_lights": ["traffic_light_right_top", "traffic_light_right_bottom"]
            }
        ]
        for intersection in key_intersections:
            for i, road1 in enumerate(self.roads):
                x1, y1, x2, y2 = road1[:4]
                if abs(x1 - intersection["x"]) < 10 and abs(y1 - intersection["y"]) < 10:
                    for j, road2 in enumerate(self.roads):
                        if i != j:
                            x3, y3, x4, y4 = road2[:4]
                            if abs(x3 - intersection["x"]) < 10 and abs(y3 - intersection["y"]) < 10:
                                self.turn_options.setdefault(i, []).append((j, (intersection["x"], intersection["y"])))
                                print(f"{self.name}: Turn option added from road {i} to road {j} at intersection ({intersection['x']}, {intersection['y']})")  

    def _process_road_properties(self):
        super()._process_road_properties()
        self._calculate_turns_at_intersections()



    def set_vehicle_registry(self, registry):
        """Set the registry of all vehicles for collision detection"""
        self.vehicle_registry = registry

    def _calculate_possible_turns(self):
        """Calculate valid turns at designated connection points"""
        self.turn_options = {}
        
        # First try using explicit road connections
        for i, road1 in enumerate(self.roads):
            road_id = road1[5] if len(road1) >= 6 else f"road_{i}"
            
            if i in self.road_connections:
                turns = []
                for j in self.road_connections[i]:
                    if i == j:  # Skip self-connections
                        continue
                        
                    road2 = self.roads[j]
                    
                    # Use the precise intersection calculation
                    intersection = get_exact_intersection_point(road1, road2)
                    
                    if intersection:
                        # Get road directions for better turns
                        road1_dir = self._get_road_direction(road1)
                        road2_dir = self._get_road_direction(road2)
                        
                        # Avoid U-turns (roads in opposite directions)
                        if not self._is_opposite_direction(road1_dir, road2_dir):
                            # Calculate angle between roads
                            x1, y1, x2, y2 = road1[:4]
                            x3, y3, x4, y4 = road2[:4]
                            angle = math.atan2(y4 - y3, x4 - x3) - math.atan2(y2 - y1, x2 - x1)
                            angle = math.degrees(angle)
                            
                            # Normalize angle to be between -180 and 180
                            angle = (angle + 180) % 360 - 180
                            
                            # Check if angle is within reasonable turning range
                            if abs(angle) <= 120:
                                int_x, int_y = int(round(intersection[0])), int(round(intersection[1]))
                                precise_intersection = (int_x, int_y)
                                turns.append((j, precise_intersection, road1_dir, road2_dir))
                                print(f"{self.name}: Road {road_id} connects to road {j} at precise intersection {precise_intersection}")
                if turns:
                    self.turn_options[i] = turns
                    print(f"{self.name}: Road {road_id} has {len(turns)} turning options")
        
        # Fall back to intersection detection if no connections defined
        if not self.turn_options:
            print(f"{self.name}: No road connections found, using strict intersection detection")
            self._calculate_turns_by_strict_intersection()  

    def _calculate_turns_by_strict_intersection(self):
        """Calculate turns using exact geometric intersections that match the map design"""
        key_intersections = [
            {"x": 50,  "y": 50},    
            {"x": 50,  "y": 250},   
            {"x": 50,  "y": 450},   
            {"x": 250, "y": 50},    
            {"x": 250, "y": 250},  
            {"x": 250, "y": 450},  
            {"x": 450, "y": 50},   
            {"x": 450, "y": 250},  
            {"x": 450, "y": 450},  
            {"x": 750, "y": 50},   
            {"x": 750, "y": 250},  
            {"x": 750, "y": 450}   
        ]
        
        for i, road1 in enumerate(self.roads):
            turns = []
            road_id = road1[5] if len(road1) >= 6 else f"road_{i}"
            
            # Check if this road passes through any key intersection
            road1_points = []
            x1, y1, x2, y2 = road1[:4]
            
            for point in key_intersections:
                # For horizontal roads
                if abs(y2 - y1) < 10:
                    if abs(y1 - point["y"]) < 10 and min(x1, x2) <= point["x"] <= max(x1, x2):
                        road1_points.append((point["x"], point["y"]))
                elif abs(x2 - x1) < 10:
                    # For vertical roads
                    if abs(x1 - point["x"]) < 10 and min(y1, y2) <= point["y"] <= max(y1, y2):
                        road1_points.append((point["x"], point["y"]))
            
            # For each intersection point on this road, find other roads that also pass through it
            for intersection in road1_points:
                for j, road2 in enumerate(self.roads):
                    if i == j:
                        continue
                    ox1, oy1, ox2, oy2 = road2[:4]
                    
                    if abs(ox2 - ox1) < 10:
                        # Vertical road
                        if abs(ox1 - intersection[0]) < 10 and min(oy1, oy2) <= intersection[1] <= max(oy1, oy2):
                            road1_dir = self._get_road_direction(road1)
                            road2_dir = self._get_road_direction(road2)
                            if not self._is_opposite_direction(road1_dir, road2_dir):
                                turns.append((j, intersection, road1_dir, road2_dir))
                    elif abs(oy2 - oy1) < 10:
                        # Horizontal road
                        if abs(oy1 - intersection[1]) < 10 and min(ox1, ox2) <= intersection[0] <= max(ox1, ox2):
                            road1_dir = self._get_road_direction(road1)
                            road2_dir = self._get_road_direction(road2)
                            if not self._is_opposite_direction(road1_dir, road2_dir):
                                turns.append((j, intersection, road1_dir, road2_dir))
            
            if turns:
                self.turn_options[i] = turns
                print(f"{self.name}: Road {road_id} has {len(turns)} strict intersection turning options")  

    def _get_road_direction(self, road):
        """Determine primary direction of a road (N, S, E, W)"""
        x1, y1, x2, y2 = road[:4]
        dx = x2 - x1
        dy = y2 - y1
        
        if abs(dx) > abs(dy):
            return "E" if dx > 0 else "W"
        else:
            return "S" if dy > 0 else "N"

    def _is_opposite_direction(self, dir1, dir2):
        """Check if two directions are opposites (N-S or E-W)"""
        opposites = {"N": "S", "S": "N", "E": "W", "W": "E"}
        return opposites.get(dir1) == dir2

    def _check_if_near_despawn_point(self):
        """Check if vehicle should despawn based on position"""
        if self.current_position in self.despawn_points and self.movement_progress > 0.9:
            return True
        return False

    def is_at_intersection(self):
        """Determine if a vehicle is at or near an intersection by checking for nearby connecting roads"""
        if self.current_position >= len(self.roads):
            return False
            
        current_road = self.roads[self.current_position]
        if len(current_road) < 6:
            return False
            
        if self.movement_progress < 0.25 or self.movement_progress > 0.75:
            x1, y1, x2, y2 = current_road[:4]
            pos_x = x1 + (x2 - x1) * self.movement_progress
            pos_y = y1 + (y2 - y1) * self.movement_progress
            
            for i, other_road in enumerate(self.roads):
                if i != self.current_position:
                    current_horizontal = abs(y2 - y1) < abs(x2 - x1)
                    ox1, oy1, ox2, oy2 = other_road[:4]
                    other_horizontal = abs(oy2 - oy1) < abs(ox2 - ox1)
                    
                    if current_horizontal != other_horizontal:
                        intersection = is_intersection(current_road, other_road)
                        if intersection:
                            ix, iy = intersection
                            distance = math.sqrt((pos_x - ix) ** 2 + (pos_y - iy) ** 2)
                            if distance < 60:
                                return True
        return False  

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> None:
        """Handle incoming messages to the vehicle agent"""
        print(f"{self.name} (Vehicle) received message: {message.content}")
        response_message = ""

        # Handle parking exit notification
        if "exit_notification" in message.content.lower():
            if self.parking_state == "parked" and self.target_parking == message.source:
                await self._exit_parking()
                response_message = f"Received exit notification from {message.source}. Initiating exit."
                print(f"{self.name} (Vehicle) responds with: {response_message}")
                return
        
        # Handle movement command
        if "move" in message.content.lower():
            # Update parking cooldown if active
            if self.parking_cooldown > 0:
                self.parking_cooldown -= 1
                print(f"{self.name}: Parking cooldown: {self.parking_cooldown} steps remaining")
            
            if self.parking_state == "parked":
                if random.random() < 0.05:
                    await self._exit_parking()
                    response_message = f"Initiating exit from parking at {self.target_parking}"
                else:
                    response_message = f"Vehicle is parked at {self.target_parking}"
            
            elif self.parking_state in ["parking", "exiting"]:
                self.parking_timer -= 1
                if self.parking_timer <= 0:
                    if self.parking_state == "parking":
                        self.parking_state = "parked"
                        response_message = f"Completed parking at {self.target_parking}"
                    else:
                        self.parking_state = "driving"
                        self.parked = False
                        if self.target_parking not in self.recent_parkings:
                            self.recent_parkings.append(self.target_parking)
                            if len(self.recent_parkings) > 3:
                                self.recent_parkings.pop(0)
                        self.parking_cooldown = random.randint(10, 20)
                        old_target = self.target_parking
                        self.target_parking = None
                        response_message = f"Exited from parking {old_target}. Cooldown: {self.parking_cooldown} steps."
                else:
                    response_message = f"Still {self.parking_state}... {self.parking_timer}s remaining"
            
            elif self.parked:
                response_message = "The vehicle is parked and cannot move."
            
            else:
                # Normal driving state
                if await self._check_for_collisions():
                    self.current_wait += 1
                    response_message = f"Cannot move due to potential collision. Wait time: {self.current_wait} sec."
                else:
                    if self.is_turning:
                        response_message = await self._continue_turn()
                    elif self.parking_cooldown <= 0 and await self._check_for_parking():
                        response_message = f"Vehicle found parking at {self.target_parking}"
                    elif self.movement_progress >= 0.95 and self.current_position in self.turn_options:
                        self.next_turn_options = self.turn_options[self.current_position]
                        should_turn = random.random() < 0.6
                        
                        if should_turn and self.next_turn_options:
                            turn_option = random.choice(self.next_turn_options)
                            next_road_idx = turn_option[0]
                            intersection_point = turn_option[1]
                            
                            if len(turn_option) > 2:
                                self.current_road_dir = turn_option[2]
                                self.target_road_dir = turn_option[3]
                            
                            print(f"{self.name} decided to turn onto road {next_road_idx} at {intersection_point}")
                            
                            if not await self._check_road_capacity(next_road_idx):
                                self.current_wait += 1
                                response_message = f"Cannot turn - target road at capacity. Wait: {self.current_wait} sec."
                            elif next_road_idx >= len(self.roads):
                                self.current_wait += 1
                                response_message = f"Cannot turn - target road {next_road_idx} is invalid."
                            else:
                                self.is_turning = True
                                self.next_road_idx = next_road_idx
                                self.intersection_point = intersection_point
                                response_message = f"Vehicle turning onto road {next_road_idx}"
                        else:
                            self.current_wait += 1
                            response_message = f"Cannot turn - no valid turn options available."
                    else:
                        response_message = await self._move_forward()

        elif "park" in message.content.lower():
            if not self.parked and self.parking_state == "driving":
                if self.parking_cooldown > 0:
                    response_message = f"Vehicle is on parking cooldown for {self.parking_cooldown} more steps."
                else:
                    parking = self._find_nearest_parking()
                    if parking:
                        self.target_parking = parking["id"]
                        parking_response = await self._request_parking(parking["id"])
                        
                        if "accepted" in parking_response:
                            try:
                                parking_time = int(parking_response.split("=")[1])
                            except (IndexError, ValueError):
                                parking_time = 3
                                
                            self.parking_state = "parking"
                            self.parking_timer = parking_time
                            self.parked = True
                            response_message = f"Started parking at {parking['id']}, time: {parking_time}s"
                        else:
                            self.target_parking = None
                            response_message = f"Parking rejected at {parking['id']}: {parking_response}"
                    else:
                        response_message = "No suitable parking areas available"
            else:
                response_message = f"Cannot park now. Current state: {self.parking_state}"
        
        elif "unpark" in message.content.lower() or "exit" in message.content.lower():
            if self.parking_state == "parked":
                await self._exit_parking()
                response_message = f"Initiating exit from {self.target_parking}"
            else:
                response_message = f"Cannot exit parking. Current state: {self.parking_state}"
        
        if response_message:
            print(f"{self.name} (Vehicle) responds with: {response_message}")
        else:
            print(f"{self.name} (Vehicle) did not generate a response.")

    async def _check_for_collisions(self):
       
        return False

    async def _continue_turn(self):
        """Continue a turn in progress"""
        if not self.is_turning:
            return "No turn in progress."
        
        # Check target road capacity
        if not await self._check_road_capacity(self.next_road_idx):
            self.current_wait += 1
            return f"Waiting to turn - target road at capacity. Wait time: {self.current_wait}"

        if self.current_wait > 0:
            self.wait_times.append(self.current_wait)
            self.current_wait = 0
        
        self.is_turning = False
        self.current_position = self.next_road_idx
        self.update_coordinates()
        self.route.append(self.current_position)
        
        return f"Vehicle completed turn onto road {self.current_position} at ({self.x:.1f}, {self.y:.1f})"

    async def _move_forward(self):
        current_xy = (self.x, self.y)
        next_xy = self.get_next_position()
        
        if not next_xy:
            return "No further road segment to follow."
            
        key_intersections = [
            # Left intersections
            {"x": 50, "y": 50},   
            {"x": 50, "y": 450},  
            # Right intersections
            {"x": 750, "y": 50},  
            {"x": 750, "y": 450}, 
            # Middle intersections
            {"x": 250, "y": 250}, 
            {"x": 450, "y": 250} 
        ]
        
        is_at_key_intersection = False
        for intersection in key_intersections:
            if is_nearby((intersection["x"], intersection["y"]), current_xy, threshold=100):
                is_at_key_intersection = True
                break
                
        if (self.movement_progress >= 0.7 and self.current_position in self.turn_options) or is_at_key_intersection:
            should_stop = False
            for light in self.traffic_lights:
                if is_nearby((light["x"], light["y"]), current_xy):
                    light_id = AgentId(light["id"], "default")
                    res = await self.runtime.send_message(
                        MyMessageType(content="request_state", source=self.name), 
                        light_id
                    )
                    if "red" in res.content.lower():
                        print(f"{self.name} stopped at red light {light['id']}")
                        should_stop = True
                        break
            
            if should_stop:
                self.current_wait += 1
                return f"Waiting due to red light. Wait time: {self.current_wait} sec."
            
            if self.current_position in self.turn_options:
                self.next_turn_options = self.turn_options[self.current_position]
                if self.next_turn_options:
                    should_turn = random.random() < 0.95
                    if should_turn:
                        turn_option = random.choice(self.next_turn_options)
                        next_road_idx = turn_option[0]
                        intersection_point = turn_option[1]
                        
                        if len(turn_option) > 2:
                            self.current_road_dir = turn_option[2]
                            self.target_road_dir = turn_option[3]
                        
                        # Force turn if we've been waiting too long
                        if await self._check_road_capacity(next_road_idx) or self.current_wait > 5 or is_at_key_intersection:
                            print(f"{self.name} turning onto road {next_road_idx} at {intersection_point}")
                            self.is_turning = True
                            self.next_road_idx = next_road_idx
                            self.intersection_point = intersection_point
                            self.movement_progress = 0.0
                            return f"Vehicle turning onto road {next_road_idx} at {intersection_point}"
                        else:
                            self.current_wait += 1
                            return f"Cannot turn - road at capacity. Wait time: {self.current_wait} sec."
        
        if self.current_wait <= 8 and await self._check_for_obstacles(current_xy):
            self.current_wait += 1
            return f"Waiting due to obstacles. Wait time: {self.current_wait} sec."
        
        if self.movement_progress >= 0.85 and self._check_if_near_despawn_point():
            print(f"{self.name} is despawning at the end of road {self.current_position}")
            return f"Vehicle {self.name} is leaving the simulation"
            
        if self.movement_progress + self.movement_step >= 1.0:
            if self.current_position in self.turn_options:
                return f"Vehicle is at an intersection, should turn."
        
        if await self._check_road_capacity(self.current_position + 1 if (self.current_position + 1 < len(self.roads)) else 0) or self.current_wait > 8:
            pass
        else:
            self.current_wait += 1
            return f"Cannot advance - next road at capacity. Wait time: {self.current_wait} sec."
        
        self.movement_progress += self.movement_step
        if self.movement_progress >= 1.0:
            next_road_idx = self.current_position + 1 if (self.current_position + 1 < len(self.roads)) else 0
            self.current_position = next_road_idx
            self.route.append(self.current_position)
            self.movement_progress = 0.0
            if self.current_wait > 0:
                self.wait_times.append(self.current_wait) 
                self.current_wait = 0
            msg = f"Vehicle moved to road segment {self.current_position}"
        else:
            msg = f"Vehicle moving along road segment {self.current_position} ({self.movement_progress:.1f})"
        
        self.update_coordinates()
        return msg

    async def _check_for_obstacles(self, position):
        x, y = position
        if self.current_wait > 10:
            print(f"{self.name} has been waiting for {self.current_wait} steps - forcing movement")
            return False
        
        key_intersections = [
            # Left intersections
            {"traffic_light": "traffic_light_left_top",    "crossing": "crossing_left_top",    "x": 50,  "y": 50},
            {"traffic_light": "traffic_light_left_bottom", "crossing": "crossing_left_bottom", "x": 50,  "y": 450},
            # Right intersections
            {"traffic_light": "traffic_light_right_top",   "crossing": "crossing_right_top",   "x": 750, "y": 50},
            {"traffic_light": "traffic_light_right_bottom","crossing": "crossing_right_bottom","x": 750, "y": 450},
            # Middle intersections
            {"traffic_light": "traffic_light_mid_left",    "crossing": "crossing_mid_2",       "x": 250, "y": 250},
            {"traffic_light": "traffic_light_mid_right",   "crossing": "crossing_mid_3",       "x": 450, "y": 250}
        ]
        
        for intersection in key_intersections:
            if is_nearby((intersection["x"], intersection["y"]), (x, y), threshold=60):
                light_id = AgentId(intersection["traffic_light"], "default")
                try:
                    res = await self.runtime.send_message(
                        MyMessageType(content="request_state", source=self.name), 
                        light_id
                    )
                    if "red" in res.content.lower():
                        print(f"{self.name} stopped at red light {intersection['traffic_light']} at key intersection")
                        return True
                    else:
                        print(f"{self.name} has green light at key intersection {intersection['traffic_light']}")
                        return False
                except Exception as e:
                    print(f"Error checking traffic light at key intersection: {e}")
        
        for light in self.traffic_lights:
            if is_nearby((light["x"], light["y"]), (x, y)):
                light_id = AgentId(light["id"], "default")
                res = await self.runtime.send_message(
                    MyMessageType(content="request_state", source=self.name), 
                    light_id
                )
                if "red" in res.content.lower():
                    print(f"{self.name} stopped at red light {light['id']}")
                    return True
        
        for crossing in self.crossings:
            if self.is_turning:
                crossing_pos = (crossing["x"], crossing["y"])
                intersection_pos = self.intersection_point
                dist_to_intersection = math.sqrt((crossing_pos[0] - intersection_pos[0])**2 + (crossing_pos[1] - intersection_pos[1])**2)
                if dist_to_intersection < 50:
                    continue
            
            if is_nearby((crossing["x"], crossing["y"]), (x, y)):
                crossing_id = AgentId(crossing["id"], "default")
                res = await self.runtime.send_message(
                    MyMessageType(content="request_state", source=self.name), 
                    crossing_id
                )
                
                if "occupied" in res.content.lower():
                    print(f"{self.name} stopped at occupied crossing {crossing['id']}")
                    return True
                    
                elif "free queue=" in res.content.lower():
                    try:
                        queue_size = int(res.content.lower().split("queue=")[1])
                        if queue_size > 10 and random.random() < 0.05:
                            print(f"{self.name} cautiously waiting at busy crossing {crossing['id']}")
                            return True
                    except (IndexError, ValueError):
                        pass
        return False

    def get_next_position(self):
        if self.is_turning:
            return self.intersection_point
        elif self.current_position + 1 < len(self.roads):
            return self.roads[self.current_position + 1][:2]
        elif len(self.roads) > 0:
            return self.roads[0][:2]
        return None

    def update_coordinates(self):
        """
        Simplified version: 
        - No partial-turn interpolation.
        - No 'teleportation prevention' checks.
        - We only do direct linear interpolation from (x1, y1) to (x2, y2)
        based on self.movement_progress.
        """
        # If we don't have a valid current_position, just bail out
        if self.current_position >= len(self.roads):
            return

        road = self.roads[self.current_position]
        # Extract the start/end coordinates of this road
        x1, y1, x2, y2 = road[:4]

        # Linear interpolation along the road
        # (movement_progress goes from 0.0 to 1.0)
        new_x = x1 + (x2 - x1) * self.movement_progress
        new_y = y1 + (y2 - y1) * self.movement_progress

        # Just set the position directly
        self.x = new_x
        self.y = new_y


    async def _check_road_capacity(self, road_index):
        if road_index < 0 or road_index >= len(self.roads):
            return False
        road = self.roads[road_index]
        if len(road) < 6:
            return True
        
        capacity = road[4]
        road_id = road[5]
        if road_id not in self.road_occupancy:
            self.road_occupancy[road_id] = 0
        
        if self.road_occupancy[road_id] < capacity:
            return True
        else:
            return False

    async def _check_for_parking(self):
        if self.parking_cooldown > 0:
            return False
        if random.random() > self.parking_desire:
            return False
        if self.is_turning:
            return False
        
        for parking in self.parking_areas:
            if parking["id"] in self.recent_parkings:
                print(f"{self.name}: Skipping recently used parking area {parking['id']}")
                continue
                
            parking_x, parking_y = parking["x"], parking["y"]
            distance = math.sqrt((self.x - parking_x)**2 + (self.y - parking_y)**2)
            print(f"{self.name}: Distance to parking {parking['id']}: {distance:.1f} units")
            if distance < 150:
                print(f"{self.name}: Found parking area {parking['id']} at distance {distance:.1f}")
                self.target_parking = parking["id"]
                parking_response = await self._request_parking(parking["id"])
                if "accepted" in parking_response:
                    try:
                        parking_time = int(parking_response.split("=")[1])
                    except (IndexError, ValueError):
                        parking_time = 3
                    self.parking_state = "parking"
                    self.parking_timer = parking_time
                    self.parked = True
                    print(f"{self.name}: Starting to park at {parking['id']}, time: {parking_time}s")
                    return True
                else:
                    self.target_parking = None
                    print(f"{self.name}: Parking rejected at {parking['id']}: {parking_response}")
        return False

    def _find_nearest_parking(self):
        """Find the nearest available parking area that hasn't been recently used"""
        nearest_parking = None
        min_distance = float('inf')
        
        for parking in self.parking_areas:
            if parking["id"] in self.recent_parkings:
                print(f"{self.name}: Skipping recently used parking area {parking['id']}")
                continue
                
            parking_x, parking_y = parking["x"], parking["y"]
            distance = math.sqrt((self.x - parking_x)**2 + (self.y - parking_y)**2)
            
            if distance < min_distance and distance < 150:
                min_distance = distance
                nearest_parking = parking
                
        if nearest_parking:
            print(f"{self.name}: Found nearest parking area {nearest_parking['id']} at distance {min_distance:.1f}")
        
        return nearest_parking

    async def _exit_parking(self):
        if not self.target_parking or self.parking_state != "parked":
            return
            
        exit_response = await self._request_exit(self.target_parking)
        if "accepted" in exit_response:
            try:
                exit_time = int(exit_response.split("=")[1])
            except (IndexError, ValueError):
                exit_time = 2
            self.parking_state = "exiting"
            self.parking_timer = exit_time
            print(f"{self.name}: Starting to exit from {self.target_parking}, time: {exit_time}s")
        else:
            print(f"{self.name}: Exit rejected from {self.target_parking}: {exit_response}")

    async def _request_parking(self, parking_id):
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
