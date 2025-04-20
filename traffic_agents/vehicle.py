import math
import random
from autogen_core import AgentId, MessageContext, message_handler
from traffic_agents.base import MyAssistant
from messages.types import MyMessageType
from shapely.geometry import LineString
from typing import Tuple
from collections import defaultdict



Point = Tuple[float, float]

def is_nearby(pos1: Point, pos2: Point, threshold: float = 30) -> bool:
    """Return True if the Euclidean distance between pos1 and pos2 is < threshold."""
    dx = pos2[0] - pos1[0]
    dy = pos2[1] - pos1[1]
    return (dx * dx + dy * dy) < threshold * threshold

def get_exact_intersection_point(road1, road2):
    line1 = LineString([(road1[0], road1[1]), (road1[2], road1[3])])
    line2 = LineString([(road2[0], road2[1]), (road2[2], road2[3])])
    inter = line1.intersection(line2)
    return tuple(inter.coords[0]) if inter.geom_type == 'Point' else None

class VehicleAssistant(MyAssistant):
    """Vehicle that handles movement, turning, parking, etc."""

    def __init__(
            self,
            name,
            current_position=0,
            start_x=None,  
            start_y=None,  
            roads=None,
            crossings=None,
            traffic_lights=None,
            parking_areas=None):
        super().__init__(name)

        self.roads = roads or []
        self.crossings = crossings or []
        self.traffic_lights = traffic_lights or []
        self.parking_areas = parking_areas or []
        self.current_position = current_position

        # Determine initial position
        initial_x = start_x
        initial_y = start_y

        # If start_x or start_y were NOT provided (are None), use the start of the current_position road
        if start_x is None or start_y is None:
            if self.current_position < len(self.roads):
                road = self.roads[self.current_position]
                if len(road) >= 2: # Ensure road has coordinates
                    initial_x = road[0]
                    initial_y = road[1]
                    print(f"{self.name}: Start position not provided, defaulting to start of road {self.current_position} at ({initial_x}, {initial_y})")
                else:
                    initial_x = 0 # Fallback if road data is incomplete
                    initial_y = 0
                    print(f"{self.name}: Warning - Start position not provided and road {self.current_position} has no coordinates. Defaulting to (0, 0).")
            else:
                initial_x = 0 # Fallback if current_position is invalid
                initial_y = 0
                print(f"{self.name}: Warning - Start position not provided and current_position {self.current_position} is invalid. Defaulting to (0, 0).")
        # Else (start_x and start_y WERE provided), use them directly.

        self.x = initial_x
        self.y = initial_y

        # Continue with other initializations
        self.movement_progress = 0.0 # Start at the beginning of its position on the road segment logic
        self.movement_step = 0.05
        self.route = [self.current_position]
        self.steps_since_start = 0

        print(f"{self.name}: Initialized at final position ({self.x}, {self.y}) on road index {current_position}")
        if current_position < len(self.roads) and len(self.roads[current_position])>=6:
            print(f"{self.name}: Starting on road {self.roads[current_position][5]}")

        # Turn logic
        self.is_turning = False
        self.next_road_idx = None
        self.turn_target = None  # intersection coords
        self.turn_origin = None
        self.turn_progress = 0.0
        self.turning_cooldown = 0
        self.last_road = None

        # Road system
        self.road_connections = {}
        self.one_way_roads = set()
        self.spawn_points = {}
        self.despawn_points = {}
        self.vehicle_registry = {}
        self.road_occupancy = {}

        # Wait times
        self.wait_times = []
        self.current_wait = 0

        # Parking
        self.parked = False
        self.parking_state = "driving"
        self.target_parking = None
        self.parking_timer = 0
        self.parking_desire = 0.3
        self.parking_cooldown = 0
        self.recent_parkings = []

        # Setup
        self._process_road_properties()
        self._validate_spawn_point()
        self._calculate_possible_turns()

    def set_vehicle_registry(self, registry):
        """Unused collision registry."""
        self.vehicle_registry = registry

    def _validate_spawn_point(self) -> None:
        """
        Pick the road segment closest to (self.x, self.y) when the agent is first
        spawned. Updates `self.current_position`, `self.movement_progress`,
        `self.route`, and `self.road_occupancy` exactly like the original method.
        """
        if not (0 <= self.current_position < len(self.roads)):
            return                 # outside road list → nothing to do

        if self.movement_progress != 0.0:      # only at spawn time
            return

        road = self.roads[self.current_position]
        if len(road) >= 4:
            print(f"{self.name}: Spawn validation check: "
                f"Position ({self.x:.1f},{self.y:.1f}) "
                f"on road index {self.current_position}")

        x0, y0 = self.x, self.y                 # cache – attribute access is slow
        best_idx = self.current_position
        best_sq  = float("inf")                 # squared distance (no sqrt yet)
        best_progress = 0.0                     # 0 = start‑point, 1 = end‑point

        def sq_dist(px: float, py: float) -> float:
            dx = px - x0
            dy = py - y0
            return dx * dx + dy * dy

        # NOTE: if this loop is still hot, pre‑filter `self.roads` once in __init__
        for i, r in enumerate(self.roads):
            if len(r) < 4:
                continue                        # skip malformed entries

            d_start = sq_dist(r[0], r[1])
            d_end   = sq_dist(r[2], r[3])
            d_sq    = d_start if d_start < d_end else d_end

            if d_sq < best_sq:                  # strictly closer?
                best_sq = d_sq
                best_idx = i
                best_progress = 0.0 if d_start < d_end else 1.0

                if best_sq == 0.0:              # perfect match – cannot beat that
                    break

        # ---------- 3) update state if we found something better ----------
        # original threshold was 100 (px) → compare against 100²
        if best_idx != self.current_position and best_sq < 10_000:
            best_dist = math.sqrt(best_sq)      # only one sqrt in the whole method
            print(f"{self.name}: Adjusted spawn road from "
                f"{self.current_position} to {best_idx} "
                f"(distance: {best_dist:.1f})")

            self.current_position  = best_idx
            self.movement_progress = best_progress
            self.route             = [best_idx]

            # update occupancy
            road = self.roads[best_idx]
            if len(road) >= 6:
                road_id = road[5]
                self.road_occupancy.setdefault(road_id, 0)
                self.road_occupancy[road_id] += 1

    def _process_road_properties(self):
        """Reads the user’s JSON road data into internal structures."""
        self.road_connections = {}
        self.one_way_roads = set()
        self.spawn_points = {}
        self.despawn_points = {}

        for i,road in enumerate(self.roads):
            # one_way
            if len(road) >= 7:
                if road[6]:
                    self.one_way_roads.add(i)
            # spawn
            if len(road) >= 8:
                if road[7]:
                    self.spawn_points[i] = True
            # despawn
            if len(road) >= 9:
                if road[8]:
                    self.despawn_points[i] = True
        # If the user has explicit connections
        for i,road in enumerate(self.roads):
            if len(road) >= 10 and isinstance(road[9], list):
                self.road_connections[i] = road[9]

        # Debug
        road_id="unknown"
        if self.current_position<len(self.roads) and len(self.roads[self.current_position])>=6:
            road_id=self.roads[self.current_position][5]
        print(f"=== {self.name} Road Props ===")
        print(f"Current road: {road_id} index={self.current_position}")
        print(f"One-ways: {len(self.one_way_roads)}")
        print(f"Spawns: {len(self.spawn_points)}")
        print(f"Despawns: {len(self.despawn_points)} => {self.despawn_points}")
        print(f"Connections: {len(self.road_connections)}")

        # If no connections exist, compute fallback
        if not self.road_connections:
            self._calculate_default_connections()

    def _calculate_default_connections(self):
        """If roads have no explicit connections, guess by geometry (end of one is near start of another)."""
        print(f"{self.name}: Calculating default connections by geometry.")
        for i,road1 in enumerate(self.roads):
            conns=[]
            x1,y1,x2,y2=road1[:4]
            end=(x2,y2)
            for j,road2 in enumerate(self.roads):
                if i==j: continue
                sx,sy=road2[0],road2[1]
                dist=math.sqrt((end[0]-sx)**2+(end[1]-sy)**2)
                if dist<60:
                    conns.append(j)
            if conns:
                self.road_connections[i]=conns
                print(f"{self.name}: Road {i} => {conns}")


    def _calculate_possible_turns(self):
        """Compute possible turns from self.road_connections plus intersection geometry if needed."""
        self.turn_options = {}
        # If you want to do “strict intersection detection,” you can add that logic here
        # or call something like self._calculate_turns_by_strict_intersection()
        # For now, we rely on self.road_connections only:
        for i,road1 in enumerate(self.roads):
            if i not in self.road_connections: 
                continue
            possible = []
            x1_curr, y1_curr, x2_curr, y2_curr = road1[:4] # End point of current road

            for j in self.road_connections[i]:
                if i==j:
                    continue
                
                road2 = self.roads[j]
                x1_next, y1_next, x2_next, y2_next = road2[:4] # Start and end of potential next road

                # compute intersection or angle checks if you want
                # For now we just store a dummy intersection = the end of road1
                # or the start of road2. Usually you want the actual intersection point:
                inter = get_exact_intersection_point(road1, road2)
                if inter:
                    # Check one-way constraint: If road 'j' is one-way, the intersection
                    # point must be closer to its start (x1_next, y1_next) than its end.
                    is_one_way_next = j in self.one_way_roads
                    if is_one_way_next:
                        dist_to_start = math.sqrt((inter[0] - x1_next)**2 + (inter[1] - y1_next)**2)
                        dist_to_end = math.sqrt((inter[0] - x2_next)**2 + (inter[1] - y2_next)**2)
                        # Allow a small tolerance (e.g., 10 units) for near-exact matches
                        if dist_to_start > dist_to_end + 10: 
                            print(f"{self.name}: Skipping turn from road {i} to one-way road {j} - wrong direction entry at {inter}.")
                            continue # Skip this turn option as it violates one-way direction

                    # get directions
                    rd1_dir = self._get_road_direction(road1)
                    rd2_dir = self._get_road_direction(road2)
                    # skip direct U-turn based on cardinal direction (already present)
                    if not self._is_opposite_direction(rd1_dir, rd2_dir):
                        possible.append( (j, inter, rd1_dir, rd2_dir) )
            if possible:
                self.turn_options[i] = possible
                # Reduced verbosity here
                # print(f"{self.name}: Road {i} has {len(possible)} turn options from connections.")

    def _get_road_direction(self, road):
        x1,y1,x2,y2=road[:4]
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx)>abs(dy):
            return "E" if dx>0 else "W"
        else:
            return "S" if dy>0 else "N"

    def _is_opposite_direction(self, d1, d2):
        """True if one is N and the other S, or E vs W."""
        opp={"N":"S","S":"N","E":"W","W":"E"}
        return opp.get(d1)==d2

    def _check_if_near_despawn_point(self):
        # A more thorough check if near the end
        if self.current_position in self.despawn_points and self.movement_progress>0.8:
            return True
        # If we have repeated the same roads multiple times
        counts={}
        for r in self.route:
            counts[r]=counts.get(r,0)+1
            if counts[r]>=3:
                return True
        # If we have been driving too long
        if self.steps_since_start>100:
            return True
        return False

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> None:
        print(f"{self.name} received: {message.content}")
        if hasattr(self,'exiting') and self.exiting:
            return
        if hasattr(self,'removed') and self.removed:
            return
        response = ""
        if "move" in message.content.lower():
            self.steps_since_start+=1
            if self.parking_state=="parked":
                # small chance to exit
                if random.random()<0.05:
                    await self._exit_parking()
                    response=f"Vehicle leaving parking {self.target_parking}"
                else:
                    response=f"Vehicle is parked at {self.target_parking}"
            elif self.parking_state in ["parking","exiting"]:
                self.parking_timer-=1
                if self.parking_timer<=0:
                    if self.parking_state=="parking":
                        self.parking_state="parked"
                        response=f"{self.name} completed parking at {self.target_parking}"
                    else:
                        self.parking_state="driving"
                        self.parked=False
                        if self.target_parking not in self.recent_parkings:
                            self.recent_parkings.append(self.target_parking)
                            if len(self.recent_parkings)>3:
                                self.recent_parkings.pop(0)
                        self.parking_cooldown = random.randint(10,20)
                        old=self.target_parking
                        self.target_parking=None
                        response=f"Exited parking {old}. cooldown={self.parking_cooldown}"
                else:
                    response=f"Still {self.parking_state}: {self.parking_timer}s"
            elif self.parked:
                response="Vehicle is parked"
            else:
                # normal movement
                if self.parking_cooldown > 0:
                    self.parking_cooldown -= 1
                
                collision=await self._check_for_collisions()
                if collision:
                    self.current_wait+=1
                    response=f"Blocked by collision? wait={self.current_wait}"
                else:
                    # maybe parking
                    found=False
                    if self.parking_cooldown<=0 and self.steps_since_start>10:
                        found=await self._check_for_parking()
                        if found:
                            response=f"Vehicle is parking at {self.target_parking}"
                    if not found:
                        response=await self._move_forward()

        if response:
            print(f"{self.name} => {response}")

    async def _check_for_collisions(self):
        return False

    async def _move_forward(self):
        """Main driving step. Also checks if turning, or if near despawn."""
        if self.is_turning:
            return await self._continue_turn()

        # check obstacles
        blocked = await self._check_for_obstacles((self.x, self.y))
        if blocked and self.current_wait < 4:  # Limit wait time to prevent vehicles from getting stuck
            self.current_wait += 1
            if self.current_wait > 3:
                print(f"{self.name} forcing movement next time.")
            return f"Waiting for obstacle. wait={self.current_wait}"

        if self.current_wait > 0:
            self.wait_times.append(self.current_wait)
            self.current_wait = 0

        # Check despawn
        if self.movement_progress > 0.85 and self._check_if_near_despawn_point():
            await self._exit_simulation()
            return f"{self.name} is despawning."

        # Possibly turn
        if self.movement_progress >= 0.75 and not self.is_turning and self.turning_cooldown <= 0:
            turned = await self._check_for_turn()
            if turned:
                self.is_turning = True
                return f"{self.name} starting turn to road {self.next_road_idx}"

        if self.turning_cooldown > 0:
            self.turning_cooldown -= 1

        # Advance
        self.movement_progress += self.movement_step
        
        # Handle road transitions when reaching the end
        if self.movement_progress >= 0.999:
            # Check if this is the last road in our route or if we're set to despawn
            if self._check_if_near_despawn_point():
                await self._exit_simulation()
                return f"{self.name} leaving sim"

            print(f"{self.name} has reached the end of road {self.current_position}")
            
            # Get current road and its end coordinates
            old_road = self.roads[self.current_position]
            end_x, end_y = old_road[2], old_road[3]  # x2, y2 of current road
            
            # Reduce occupancy for the road we're leaving
            if len(old_road) >= 6:
                road_id = old_road[5]
                if road_id in self.road_occupancy and self.road_occupancy[road_id] > 0:
                    self.road_occupancy[road_id] -= 1
                    print(f"{self.name}: Leaving road {road_id}, occupancy now {self.road_occupancy[road_id]}")
            
            # Store the road we're leaving
            self.last_road = self.current_position
            
            # Get the next road to transition to
            next_road_idx = self._get_next_road()
            print(f"{self.name} moving from road {self.current_position} to road {next_road_idx}")
            
            # Get the new road and compute the parameter t at the intersection point
            new_road = self.roads[next_road_idx]
            
            # Compute parameter on new road based on the endpoint of old road
            param = self._compute_parameter_on_road(new_road, end_x, end_y)
            print(f"{self.name}: Starting new road at parameter {param:.3f} instead of 0.0")
            
            # Update to the new road with the correct parameter
            self.current_position = next_road_idx
            self.movement_progress = param  # Use intersection parameter instead of resetting to 0.0
            self.route.append(self.current_position)
            
            # Update occupancy for the new road
            if len(new_road) >= 6:
                road_id = new_road[5]
                if road_id not in self.road_occupancy:
                    self.road_occupancy[road_id] = 0
                self.road_occupancy[road_id] += 1
                print(f"{self.name}: Entering road {road_id}, occupancy now {self.road_occupancy[road_id]}")
            
            # Update coordinates based on the parameter on the new road
            self.update_coordinates()
            
            return f"Vehicle moved to road segment {self.current_position} at parameter {param:.3f}"
        else:
            # Just continue moving along current road
            self.update_coordinates()
            return f"Vehicle moving along road segment {self.current_position} ({self.movement_progress:.2f})"

    async def _continue_turn(self):
        """Continue turning until the turn arc is finished, then place the vehicle onto the new road at the intersection."""
        if not self.is_turning:
            return "No turn in progress."

        # Check if the target road has capacity
        if not await self._check_road_capacity(self.next_road_idx):
            self.current_wait += 1
            return f"Waiting to turn - target road {self.next_road_idx} at capacity. Wait time: {self.current_wait}"

        # Reset wait counter if we were waiting
        if self.current_wait > 0:
            self.wait_times.append(self.current_wait)
            self.current_wait = 0

        # Progress the turn animation
        self.turn_progress += 0.15  # Adjust turn speed as needed
        
        # Turn completed
        if self.turn_progress >= 1.0:
            # Update road transition tracking
            self.last_road = self.current_position
            self.current_position = self.next_road_idx
            self.route.append(self.current_position)
            self.is_turning = False
            self.turning_cooldown = 5  # Cooldown before next turn
            
            # Get the final intersection coordinates
            ix, iy = self._turn_arc_position(1.0)
            
            # Get the new road and compute the correct parameter
            new_road = self.roads[self.current_position]
            param = self._compute_parameter_on_road(new_road, ix, iy)
            
            # Update movement progress to the parameter on the new road
            self.movement_progress = param  # NOT resetting to 0.0
            
            # Set position exactly at the intersection point
            self.x, self.y = ix, iy
            
            # Update road occupancy
            if len(new_road) >= 6:
                road_id = new_road[5]
                if road_id not in self.road_occupancy:
                    self.road_occupancy[road_id] = 0
                self.road_occupancy[road_id] += 1
                print(f"{self.name}: Entering road {road_id} after turn, occupancy now {self.road_occupancy[road_id]}")
            
            return f"Vehicle completed turn onto road {self.current_position} at parameter {param:.3f}, position: ({ix:.1f}, {iy:.1f})"
        else:
            # Compute position along the turn arc for partial turns
            px, py = self._turn_arc_position(self.turn_progress)
            self.x, self.y = px, py
            return f"Vehicle turning to road {self.next_road_idx}, turn progress: {self.turn_progress:.2f}"

    def _turn_arc_position(self, progress):
        """Calculate position along a turn arc at the given progress (0.0 to 1.0)"""
        if not hasattr(self, 'turn_origin') or not hasattr(self, 'turn_target'):
            return self.x, self.y
            
        # Get positions
        origin_x, origin_y = self.turn_origin
        target_x, target_y = self.turn_target
        
        # Use cubic easing for smooth turn motion
        t = progress
        eased_t = t * t * (3 - 2 * t)  # Smooth ease-in-ease-out curve
        
        # Intermediate position
        x = origin_x + (target_x - origin_x) * eased_t
        y = origin_y + (target_y - origin_y) * eased_t
        
        return x, y

    def _compute_parameter_on_road(self, road, x, y):
        """Compute the parameter t (0.0 to 1.0) for a point (x,y) on a road segment"""
        x1, y1, x2, y2 = road[:4]
        
        # Calculate road vector
        road_vector_x = x2 - x1
        road_vector_y = y2 - y1
        road_length_squared = road_vector_x**2 + road_vector_y**2
        
        if road_length_squared < 0.0001:  # Avoid division by zero
            return 0.0
            
        # Calculate vector from road start to point
        point_vector_x = x - x1
        point_vector_y = y - y1
        
        # Project point vector onto road vector (dot product)
        projection = (point_vector_x * road_vector_x + point_vector_y * road_vector_y) / road_length_squared
        
        # Clamp to [0,1] to ensure we stay on the road segment
        parameter = max(0.0, min(1.0, projection))
        
        print(f"{self.name}: Computed parameter {parameter:.3f} for point ({x:.1f},{y:.1f}) on road segment")
        return parameter


    def update_coordinates(self):
        """Linear interpolation along current road using movement_progress."""
        if self.current_position>=len(self.roads):
            return
        r=self.roads[self.current_position]
        x1,y1,x2,y2=r[:4]
        t=self.movement_progress
        self.x=x1+(x2-x1)*t
        self.y=y1+(y2-y1)*t

    async def _check_road_capacity(self, road_idx):
        if road_idx<0 or road_idx>=len(self.roads):
            return False
        road=self.roads[road_idx]
        if len(road)<6:
            return True
        cap=road[4]
        rdid=road[5]
        if rdid not in self.road_occupancy:
            self.road_occupancy[rdid]=0
        return (self.road_occupancy[rdid]<cap)

    async def _check_for_obstacles(self, position):
        """Check lights/ped crossings. Return True if blocked."""
        x,y=position
        # Traffic lights
        for light in self.traffic_lights:
            if is_nearby((light["x"],light["y"]),(x,y),threshold=50):
                light_id=AgentId(light["id"],"default")
                try:
                    res=await self.runtime.send_message(
                        MyMessageType(content="request_state",source=self.name),
                        light_id
                    )
                    if "red" in res.content.lower():
                        print(f"{self.name} blocked at red light {light['id']}")
                        return True
                except:
                    if self.current_wait>2:
                        return False
                    return True
        # Crossings
        for crossing in self.crossings:
            if is_nearby((crossing["x"],crossing["y"]),(x,y),threshold=40):
                crossing_id=AgentId(crossing["id"],"default")
                try:
                    res=await self.runtime.send_message(
                        MyMessageType(content="request_state",source=self.name),
                        crossing_id
                    )
                    if "occupied" in res.content.lower():
                        if self.current_wait>=3:
                            return False
                        return True
                except:
                    if self.current_wait>1:
                        return False
                    return True

        if self.current_wait>4:
            self.current_wait=0
            return False
        return False

    async def _check_for_parking(self):
        if self.parking_cooldown>0:
            return False
        if random.random()>self.parking_desire:
            return False
        for p in self.parking_areas:
            if p["id"] in self.recent_parkings:
                continue
            dist=math.sqrt((self.x-p["x"])**2+(self.y-p["y"])**2)
            if dist<150:
                self.target_parking=p["id"]
                resp=await self._request_parking(self.target_parking)
                if "accepted" in resp:
                    try:
                        sec=int(resp.split("=")[1])
                    except:
                        sec=3
                    self.parking_state="parking"
                    self.parking_timer=sec
                    self.parked=True
                    return True
                else:
                    self.target_parking=None
        return False

    async def _exit_parking(self):
        if not self.target_parking or self.parking_state!="parked":
            return
        resp=await self._request_exit(self.target_parking)
        if "accepted" in resp:
            try:
                sec=int(resp.split("=")[1])
            except:
                sec=2
            self.parking_state="exiting"
            self.parking_timer=sec

    async def _request_parking(self, pid):
        try:
            aid=AgentId(pid,"default")
            r=await self.runtime.send_message(
                MyMessageType(content="park",source=self.name),
                aid
            )
            return r.content
        except:
            return "error"

    async def _request_exit(self, pid):
        try:
            aid=AgentId(pid,"default")
            r=await self.runtime.send_message(
                MyMessageType(content="exit",source=self.name),
                aid
            )
            return r.content
        except:
            return "error"

    def _get_next_road(self):
        """Pick next road from explicit connections or fallback to i+1."""
        if self.current_position in self.road_connections:
            options=self.road_connections[self.current_position]
            if options:
                if self.last_road is not None:
                    filtered=[o for o in options if o!=self.last_road]
                    if filtered:
                        return random.choice(filtered)
                return random.choice(options)
        # fallback: check turn_options
        if self.current_position in self.turn_options:
            tlist=self.turn_options[self.current_position]
            if tlist:
                roads=[x[0] for x in tlist]
                if self.last_road is not None:
                    filtered=[r for r in roads if r!=self.last_road]
                    if filtered:
                        return random.choice(filtered)
                return random.choice(roads)
        # final fallback
        idx=(self.current_position+1)%len(self.roads)
        if idx==self.current_position:
            idx=(idx+1)%len(self.roads)
        return idx

    async def _exit_simulation(self):
        self.exiting=True
        self.removed=True
        self.x=-9999
        self.y=-9999
        self.parked=False
        self.parking_state="exited"
        # try manager
        try:
            sim_mgr=AgentId("simulation_manager","default")
            await self.runtime.send_message(
                MyMessageType(content=f"exit_notification|{self.name}",source=self.name),
                sim_mgr
            )
        except:
            pass
        print(f"{self.name} EXITING SIMULATION ⚠️")
        return True

    async def _check_for_turn(self):
        """Check if we should turn at this point, based on road connections and turn options."""
        # Check if we're at an eligible turning progress
        if self.movement_progress < 0.75 or self.is_turning:
            return False
            
        # Skip if we just turned (cooldown)
        if self.turning_cooldown > 0:
            return False
            
        current_road = self.roads[self.current_position]
        road_id = current_road[5] if len(current_road) >= 6 else f"road_{self.current_position}"
        
        # Get current position on road
        x1, y1, x2, y2 = current_road[:4]
        current_x = x1 + (x2 - x1) * self.movement_progress
        current_y = y1 + (y2 - y1) * self.movement_progress
        
        # Check turn options from our pre-calculated list
        if self.current_position in self.turn_options and self.turn_options[self.current_position]:
            # Get random turn weighted by direction (prefer continuing in same direction)
            weights = []
            options = []
            
            current_direction = self._get_road_direction(current_road)
            
            for next_road_idx, intersection, from_dir, to_dir in self.turn_options[self.current_position]:
                # Skip turning to the road we just came from
                if next_road_idx == self.last_road:
                    continue
                    
                # Check if the next road has capacity
                if not await self._check_road_capacity(next_road_idx):
                    continue
                    
                # Calculate weight based on direction change
                weight = 1.0
                # Prefer continuing in same direction
                if from_dir == to_dir:
                    weight = 3.0  # Much higher weight for continuing straight
                # Lower weight for U-turns
                elif self._is_opposite_direction(from_dir, to_dir):
                    weight = 0.2  # Much lower weight for U-turns
                
                # Add to options
                options.append((next_road_idx, intersection))
                weights.append(weight)
                
            # If we have options, select one weighted by direction preference
            if options:
                # Normalize weights
                total = sum(weights)
                if total > 0:
                    weights = [w/total for w in weights]
                    
                # Use the weights for selection
                if random.random() < 0.9:  # 90% chance to use weighted selection
                    # Weighted random selection
                    r = random.random()
                    cumulative = 0
                    selected_idx = 0
                    for i, w in enumerate(weights):
                        cumulative += w
                        if r <= cumulative:
                            selected_idx = i
                            break
                    selected = options[selected_idx]
                else:
                    # Pure random 10% of the time
                    selected = random.choice(options)
                
                # Set up the turn
                self.next_road_idx, intersection_point = selected
                next_road = self.roads[self.next_road_idx]
                next_road_id = next_road[5] if len(next_road) >= 6 else f"road_{self.next_road_idx}"
                
                # Store origin and target to compute the turn arc
                self.turn_origin = (current_x, current_y)
                self.turn_target = intersection_point
                self.turn_progress = 0.0
                
                print(f"{self.name} beginning turn from {road_id} to {next_road_id} at intersection {intersection_point}")
                
                return True
        
        # Check if we should turn based on connections even if not at a detected intersection
        if self.movement_progress > 0.85 and self.current_position in self.road_connections:
            options = self.road_connections[self.current_position]
            valid_options = []
            
            for next_idx in options:
                # Skip the road we just came from
                if next_idx == self.last_road:
                    continue
                    
                # Check if the road has capacity
                if not await self._check_road_capacity(next_idx):
                    continue
                    
                valid_options.append(next_idx)
                
            if valid_options:
                # Select a random option
                self.next_road_idx = random.choice(valid_options)
                next_road = self.roads[self.next_road_idx]
                next_road_id = next_road[5] if len(next_road) >= 6 else f"road_{self.next_road_idx}"
                
                # Use road endpoints for turn calculation
                self.turn_origin = (current_x, current_y)
                
                # Try to find intersection point
                intersection = get_exact_intersection_point(current_road, next_road)
                if intersection:
                    self.turn_target = intersection
                else:
                    # Fallback to start of next road
                    self.turn_target = (next_road[0], next_road[1])
                    
                self.turn_progress = 0.0
                
                print(f"{self.name} beginning turn from {road_id} to {next_road_id} at calculated intersection {self.turn_target}")
                
                return True
                
        # No valid turns found
        return False
