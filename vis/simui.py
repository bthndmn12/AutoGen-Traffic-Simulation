import tkinter as tk
import asyncio

class MapObject:
    def __init__(self, id, x, y):
        self.id = id
        self.x = x
        self.y = y

    def render(self, canvas):
        raise NotImplementedError("Subclasses should implement render method")

class RoadObject:
    def __init__(self, x1, y1, x2, y2, color="gray", width=20, capacity=2, road_id=None):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.base_color = color  # Store the original color
        self.current_color = color  # Color that will be displayed
        self.width = width
        self.capacity = capacity
        self.road_id = road_id
        self.current_vehicles = 0  # Track current number of vehicles on road
        
    def render(self, canvas):
        # Only change color based on capacity if the road wasn't specifically set to be red
        if self.base_color != "red":
            # Adjust color based on capacity utilization
            self.current_color = self.base_color
            if hasattr(self, 'current_vehicles') and self.capacity > 0:
                if self.current_vehicles >= self.capacity:
                    self.current_color = "orange"  # Road at capacity (changed from red to orange)
                elif self.current_vehicles >= self.capacity * 0.7:
                    self.current_color = "yellow"  # Road approaching capacity
        else:
            # Always use the base color if it was explicitly set to red
            self.current_color = self.base_color
        
        canvas.create_line(self.x1, self.y1, self.x2, self.y2, fill=self.current_color, width=self.width)
        
        # Add small markers at the ends of roads for better visibility
        canvas.create_oval(self.x1-5, self.y1-5, self.x1+5, self.y1+5, fill="black")
        canvas.create_oval(self.x2-5, self.y2-5, self.x2+5, self.y2+5, fill="black")
        
        # Display road ID and capacity if available
        if self.road_id:
            # Calculate midpoint of the road
            mid_x = self.x1 + (self.x2 - self.x1) / 2
            mid_y = self.y1 + (self.y2 - self.y1) / 2
            
            # Display road ID and capacity
            capacity_text = f"{self.road_id} ({self.current_vehicles}/{self.capacity})"
            canvas.create_text(mid_x, mid_y - 15, text=capacity_text, fill="black", font=("Arial", 8))

class ParkingAreaObject(MapObject):
    def __init__(self, id, agent, x=200, y=200, width=40, height=30, parking_type="street"):
        super().__init__(id, x, y)
        self.agent = agent
        self.width = width
        self.height = height
        self.parking_type = parking_type
        
    def render(self, canvas):
        if self.agent:
            # Determine color based on occupancy
            if hasattr(self.agent, 'is_full') and self.agent.is_full:
                fill_color = "red"
            elif hasattr(self.agent, 'current_occupancy') and hasattr(self.agent, 'capacity'):
                occupancy_ratio = self.agent.current_occupancy / self.agent.capacity
                if occupancy_ratio >= 0.7:
                    fill_color = "orange"
                else:
                    fill_color = "blue"
            else:
                fill_color = "blue"
                
            # Adjust size based on type
            if self.parking_type == "building":
                width, height = self.width * 1.5, self.height * 1.5
                # Draw parking building (larger rectangle with roof)
                canvas.create_rectangle(
                    self.x - width/2, self.y - height/2,
                    self.x + width/2, self.y + height/2,
                    fill=fill_color, outline="black", width=2
                )
                # Add a roof
                canvas.create_polygon(
                    self.x - width/2, self.y - height/2,
                    self.x, self.y - height/2 - 15,
                    self.x + width/2, self.y - height/2,
                    fill="darkblue", outline="black"
                )
            else:
                width, height = self.width, self.height
                # Draw street parking (rectangle with P symbol)
                canvas.create_rectangle(
                    self.x - width/2, self.y - height/2,
                    self.x + width/2, self.y + height/2,
                    fill=fill_color, outline="black", width=2
                )
                
            # Add parking symbol
            canvas.create_text(
                self.x, self.y, 
                text="P", 
                fill="white", 
                font=("Arial", 12, "bold")
            )
            
            # Add status text
            if hasattr(self.agent, 'current_occupancy') and hasattr(self.agent, 'capacity'):
                status_text = f"{self.id} ({self.agent.current_occupancy}/{self.agent.capacity})"
            else:
                status_text = self.id
                
            canvas.create_text(
                self.x, self.y - height/2 - 10,
                text=status_text,
                fill="black",
                font=("Arial", 9)
            )
        else:
            # Fallback if no agent
            canvas.create_rectangle(
                self.x - self.width/2, self.y - self.height/2,
                self.x + self.width/2, self.y + self.height/2,
                fill="gray", outline="black"
            )
            canvas.create_text(self.x, self.y - self.height/2 - 10, text=f"{self.id} (no agent)")

class VehicleObject(MapObject):
    def __init__(self, id, agent, x=50, y=300):
        super().__init__(id, x, y)
        self.agent = agent
        self.color_cycle = ["blue", "cyan", "navy", "purple"]

    def render(self, canvas):
        if self.agent:
            # Get position from agent, ensuring we convert any floats to integers for the canvas
            # We use self.x and self.y which already include the offset (set by the visualizer)
            position_x = int(self.x)
            position_y = int(self.y)
            
            # Determine vehicle color based on state and wait time
            if hasattr(self.agent, 'parking_state'):
                if self.agent.parking_state == "parked":
                    color = "darkgreen"
                elif self.agent.parking_state in ["parking", "exiting"]:
                    color = "darkblue"
                elif self.agent.parked:
                    color = "purple"
                else:
                    color = self.color_cycle[sum(self.agent.wait_times) % len(self.color_cycle)]
            else:
                color = self.color_cycle[sum(self.agent.wait_times) % len(self.color_cycle)]
            
            # Draw a more visible vehicle
            canvas.create_rectangle(position_x - 15, position_y - 15, 
                                  position_x + 15, position_y + 15, 
                                  fill=color, outline='black', width=2)
            
            # Draw direction indicators (simple arrow shape based on road direction)
            if hasattr(self.agent, 'current_position') and not getattr(self.agent, 'parked', False) and self.agent.current_position < len(self.agent.roads):
                road = self.agent.roads[self.agent.current_position]
                # Unpack coordinates, ensuring we handle both old and new road tuple formats
                x1, y1, x2, y2 = road[:4]  # First 4 elements are coordinates
                
                # Determine if road is more horizontal or vertical
                if abs(x2 - x1) > abs(y2 - y1):  # Horizontal road
                    dx = 10 if x2 > x1 else -10
                    canvas.create_line(position_x, position_y, position_x + dx, position_y, 
                                     arrow="last", width=2, fill="white")
                else:  # Vertical road
                    dy = 10 if y2 > y1 else -10
                    canvas.create_line(position_x, position_y, position_x, position_y + dy, 
                                     arrow="last", width=2, fill="white")
            
            # Draw the vehicle ID and position info
            status_info = ""
            if hasattr(self.agent, 'parking_state') and self.agent.parking_state != "driving":
                if self.agent.parking_state == "parked":
                    status_info = f" (PARKED at {self.agent.target_parking})"
                else:
                    status_info = f" ({self.agent.parking_state.upper()})"
            elif hasattr(self.agent, 'movement_progress'):
                status_info = f" ({int(self.agent.movement_progress*100)}%)"
            
            # Display agent's real coordinates, not the canvas-adjusted ones
            agent_real_x = int(getattr(self.agent, "x", 0))
            agent_real_y = int(getattr(self.agent, "y", 0))
            canvas.create_text(position_x, position_y - 25, 
                              text=f"{self.id} ({agent_real_x}, {agent_real_y}){status_info}",
                              fill="black", font=("Arial", 10, "bold"))
        else:
            canvas.create_rectangle(self.x - 15, self.y - 15, 
                                  self.x + 15, self.y + 15, 
                                  fill='gray', outline='black')
            canvas.create_text(self.x, self.y - 25, text=f"{self.id} (no agent)")


class TrafficLightObject(MapObject):
    def __init__(self, id, agent, x=300, y=250):
        super().__init__(id, x, y)
        self.agent = agent

    def render(self, canvas):
        if self.agent:
            light_color = "green" if self.agent.state.upper() == "GREEN" else "red"
            # Draw larger traffic light for better visibility
            canvas.create_oval(self.x - 10, self.y - 10, 
                             self.x + 10, self.y + 10, 
                             fill=light_color, outline='black', width=2)
            canvas.create_text(self.x, self.y - 20, text=f"{self.id}")
        else:
            canvas.create_oval(self.x - 10, self.y - 10, 
                             self.x + 10, self.y - 10, 
                             fill="gray", outline='black')
            canvas.create_text(self.x, self.y - 20, text=f"{self.id} (no agent)")


class PedestrianCrossingObject(MapObject):
    def __init__(self, id, agent, x=320, y=270):
        super().__init__(id, x, y)
        self.agent = agent

    def render(self, canvas):
        if self.agent:
            color = "orange" if self.agent.is_occupied else "white"
            # Make crossing more visible
            canvas.create_rectangle(self.x - 15, self.y - 15, 
                                   self.x + 15, self.y + 15, 
                                   fill=color, outline='black', width=2)
            # Add striped pattern for crosswalk
            if not self.agent.is_occupied:
                for i in range(-12, 13, 8):
                    canvas.create_line(self.x - 15, self.y + i, 
                                      self.x + 15, self.y + i, 
                                      fill="black", width=2)
            
            canvas.create_text(self.x, self.y - 25, text=f"{self.id}")
        else:
            canvas.create_rectangle(self.x - 15, self.y - 15, 
                                   self.x + 15, self.y + 15, 
                                   fill="gray", outline='black')
            canvas.create_text(self.x, self.y - 25, text=f"{self.id} (no agent)")

class TrafficSimulationVisualizer:
    def __init__(self, width=900, height=650):
        self.running = True
        self.objects = []  # List[MapObject]
        self.root = tk.Tk()
        self.root.title("Traffic Simulation Visualizer")
        
        # Configure the window
        self.width = width
        self.height = height
        self.root.geometry(f"{width}x{height}")  # Extra space for info panels
        self.root.configure(bg="#f0f0f0")  # Light gray background
        
        # Center the window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_cordinate = int((screen_width/2) - (width)/2)
        y_cordinate = int((screen_height/2) - (height)/2)
        self.root.geometry(f"+{x_cordinate}+{y_cordinate}")
        
        # Create a frame for better padding and border
        self.main_frame = tk.Frame(self.root, bg="#f0f0f0", padx=20, pady=20)
        self.main_frame.pack(fill="both", expand=True)
        
        # Add a title label
        self.title_label = tk.Label(
            self.main_frame, 
            text="Traffic Simulation", 
            font=("Arial", 16, "bold"),
            bg="#f0f0f0", 
            fg="#333333"
        )
        self.title_label.pack(pady=(0, 10))
        
        # Canvas with border and drop shadow effect
        self.canvas_frame = tk.Frame(
            self.main_frame, 
            bg="#d0d0d0",  # Border color
            highlightbackground="#a0a0a0",
            highlightthickness=1
        )
        self.canvas_frame.pack(padx=5, pady=5)
        
        # The actual canvas for drawing
        self.canvas = tk.Canvas(
            self.canvas_frame, 
            width=width, 
            height=height, 
            bg="white",
            highlightthickness=0
        )
        self.canvas.pack(padx=2, pady=2)
        
        # Information panel
        self.info_frame = tk.Frame(self.main_frame, bg="#f0f0f0", pady=5)
        self.info_frame.pack(fill="x")
        
        # Status label
        self.status_label = tk.Label(
            self.info_frame, 
            text="Simulation Status: Running", 
            bg="#f0f0f0", 
            fg="#333333",
            font=("Arial", 10)
        )
        self.status_label.pack(side="left", padx=5)
        
        # Information label for objects
        self.info_label = tk.Label(
            self.info_frame, 
            text="", 
            bg="#f0f0f0", 
            fg="#333333",
            font=("Arial", 9),
            justify="left",
            anchor="w"
        )
        self.info_label.pack(side="right", padx=5, fill="x", expand=True)
        
        # Control buttons frame
        self.control_frame = tk.Frame(self.main_frame, bg="#f0f0f0", pady=5)
        self.control_frame.pack(fill="x")
        
        # Dictionary to store road objects by ID
        self.road_objects = {}
        
        # Rendering offsets to center the map in the canvas
        self.offset_x = width // 2  # Center horizontally
        self.offset_y = height // 2  # Center vertically
        
        # Map boundaries for auto-centering
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.min_y = float('inf')
        self.max_y = float('-inf')

    def add_object(self, obj):
        print(f"Added object: {getattr(obj, 'id', obj.__class__.__name__)}")
        self.objects.append(obj)
        
        # Store road objects in a dictionary for quick lookup
        if isinstance(obj, RoadObject) and obj.road_id:
            self.road_objects[obj.road_id] = obj
            
        # Update map boundaries based on object position
        if isinstance(obj, RoadObject):
            self.min_x = min(self.min_x, obj.x1, obj.x2)
            self.max_x = max(self.max_x, obj.x1, obj.x2)
            self.min_y = min(self.min_y, obj.y1, obj.y2)
            self.max_y = max(self.max_y, obj.y1, obj.y2)
        elif hasattr(obj, 'x') and hasattr(obj, 'y'):
            self.min_x = min(self.min_x, obj.x)
            self.max_x = max(self.max_x, obj.x)
            self.min_y = min(self.min_y, obj.y)
            self.max_y = max(self.max_y, obj.y)
        
        # Recalculate the center offset based on the object boundaries
        if self.min_x != float('inf') and self.max_x != float('-inf'):
            map_center_x = (self.min_x + self.max_x) / 2
            map_center_y = (self.min_y + self.max_y) / 2
            
            # Calculate offset to center the map
            self.offset_x = self.width/2 - map_center_x
            self.offset_y = self.height/2 - map_center_y

    async def run(self):
        # Final calculation of the center before starting
        self._calculate_map_center()
        
        while self.running:
            # Update roads with current vehicle count
            self.update_road_vehicle_counts()
            
            # Clear and redraw everything
            self.canvas.delete("all")
            self.draw_background()
            
            # Apply transformations to center the map
            self.canvas.create_text(
                self.width/2, 20, 
                text=f"Map centered at offset: ({int(self.offset_x)}, {int(self.offset_y)})", 
                fill="#666666", 
                font=("Arial", 8)
            )
            
            # Draw roads first, then other objects on top
            for obj in sorted(self.objects, key=lambda x: not isinstance(x, RoadObject)):
                if isinstance(obj, RoadObject):
                    # Center road objects
                    obj_copy = RoadObject(
                        obj.x1 + self.offset_x, obj.y1 + self.offset_y,
                        obj.x2 + self.offset_x, obj.y2 + self.offset_y,
                        obj.base_color, obj.width, obj.capacity, obj.road_id
                    )
                    obj_copy.current_vehicles = obj.current_vehicles
                    obj_copy.render(self.canvas)
                elif isinstance(obj, MapObject):
                    if isinstance(obj, VehicleObject) and obj.agent:
                        # For vehicles with agents, use the agent's actual coordinates
                        agent_x = getattr(obj.agent, "x", 0)
                        agent_y = getattr(obj.agent, "y", 0)
                        
                        # Create a copy of the object with properly offset coordinates
                        temp_vehicle = VehicleObject(
                            obj.id,
                            obj.agent,
                            x=agent_x + self.offset_x,
                            y=agent_y + self.offset_y
                        )
                        temp_vehicle.render(self.canvas)
                    else:
                        # For non-vehicle objects, create a temporary centered copy
                        obj_class = obj.__class__
                        if isinstance(obj, (TrafficLightObject, PedestrianCrossingObject, ParkingAreaObject)):
                            centered_obj = obj_class(obj.id, obj.agent, 
                                                 obj.x + self.offset_x, obj.y + self.offset_y)
                            if hasattr(obj, 'width') and hasattr(obj, 'height'):
                                centered_obj.width = obj.width
                                centered_obj.height = obj.height
                            if hasattr(obj, 'parking_type'):
                                centered_obj.parking_type = obj.parking_type
                        else:
                            # Generic handling for other MapObject types
                            centered_obj = obj_class(obj.id, obj.x + self.offset_x, obj.y + self.offset_y)
                        
                        centered_obj.render(self.canvas)

            self.update_info_label()
            self.root.update()
            await asyncio.sleep(0.1)
        self.root.destroy()
        
    def _calculate_map_center(self):
        """Calculate the center of the map based on object positions"""
        if len(self.objects) == 0:
            return  # No objects, use default center
            
        # Reset boundaries
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.min_y = float('inf')
        self.max_y = float('-inf')
        
        # Find the bounds of all objects
        for obj in self.objects:
            if isinstance(obj, RoadObject):
                self.min_x = min(self.min_x, obj.x1, obj.x2)
                self.max_x = max(self.max_x, obj.x1, obj.x2)
                self.min_y = min(self.min_y, obj.y1, obj.y2)
                self.max_y = max(self.max_y, obj.y1, obj.y2)
            elif hasattr(obj, 'x') and hasattr(obj, 'y'):
                self.min_x = min(self.min_x, obj.x)
                self.max_x = max(self.max_x, obj.x)
                self.min_y = min(self.min_y, obj.y)
                self.max_y = max(self.max_y, obj.y)
        
        # Only calculate if we have valid bounds
        if self.min_x != float('inf') and self.max_x != float('-inf'):
            map_center_x = (self.min_x + self.max_x) / 2
            map_center_y = (self.min_y + self.max_y) / 2
            
            # Calculate offset to center the map
            self.offset_x = self.width/2 - map_center_x
            self.offset_y = self.height/2 - map_center_y
            
            print(f"Map centered at offset: ({self.offset_x}, {self.offset_y})")

    def update_road_vehicle_counts(self):
        """Update the current vehicle count on each road segment"""
        # Reset all road counts
        for road_obj in self.road_objects.values():
            road_obj.current_vehicles = 0
            
        # Count vehicles on each road
        for obj in self.objects:
            if isinstance(obj, VehicleObject) and obj.agent and hasattr(obj.agent, 'current_position'):
                # Only count vehicles that are driving (not parked)
                if hasattr(obj.agent, 'parking_state') and obj.agent.parking_state != "driving":
                    continue
                    
                if obj.agent.current_position < len(obj.agent.roads):
                    road = obj.agent.roads[obj.agent.current_position]
                    if len(road) >= 6:  # Make sure road has capacity and ID
                        road_id = road[5]  # Road ID is the 6th element
                        if road_id in self.road_objects:
                            self.road_objects[road_id].current_vehicles += 1

    def draw_background(self):
        # Draw a cleaner grid with lighter colors
        for i in range(0, self.width, 100):
            self.canvas.create_line(i, 0, i, self.height, fill="#e0e0e0", dash=(4, 4))
            self.canvas.create_text(i, 10, text=str(i), fill="#909090", font=("Arial", 8))
        
        for i in range(0, self.height, 100):
            self.canvas.create_line(0, i, self.width, i, fill="#e0e0e0", dash=(4, 4))
            self.canvas.create_text(10, i, text=str(i), fill="#909090", font=("Arial", 8))

    def update_info_label(self):
        # Sort objects by type for better organization
        vehicle_info = []
        traffic_light_info = []
        crossing_info = []
        parking_info = []
        
        # Collect information by category
        for obj in self.objects:
            if isinstance(obj, VehicleObject) and obj.agent:
                status_info = ""
                if hasattr(obj.agent, 'parking_state') and obj.agent.parking_state != "driving":
                    status_info = f" [{obj.agent.parking_state}]"
                elif hasattr(obj.agent, 'movement_progress'):
                    progress_info = f" ({int(obj.agent.movement_progress*100)}%)"
                    status_info = progress_info
                    
                road_info = ""
                if hasattr(obj.agent, 'current_position') and obj.agent.current_position < len(obj.agent.roads) and obj.agent.parking_state == "driving":
                    road = obj.agent.roads[obj.agent.current_position]
                    if len(road) >= 6:
                        road_id = road[5]
                        road_info = f" on {road_id}"
                        
                parking_info_text = ""
                if hasattr(obj.agent, 'target_parking') and obj.agent.target_parking:
                    parking_info_text = f" → {obj.agent.target_parking}"
                    
                vehicle_info.append(f"Vehicle {obj.id}: Pos {obj.agent.current_position}{status_info}{road_info}{parking_info_text}")
                
            # Traffic light information
            elif isinstance(obj, TrafficLightObject) and obj.agent:
                traffic_light_info.append(f"Light {obj.id}: {obj.agent.state}")
                
            # Pedestrian crossing information
            elif isinstance(obj, PedestrianCrossingObject) and obj.agent:
                status = "occupied" if obj.agent.is_occupied else "free"
                crossing_info.append(f"Crossing {obj.id}: {status}")
                
            # Parking area information
            elif isinstance(obj, ParkingAreaObject) and obj.agent:
                capacity_info = f" ({obj.agent.current_occupancy}/{obj.agent.capacity})"
                parking_info.append(f"Parking {obj.id}{capacity_info}")

        # Create categories for better organization
        all_info = []
        if vehicle_info:
            all_info.append("Vehicles: " + " | ".join(vehicle_info))
        if traffic_light_info:
            all_info.append("Lights: " + " | ".join(traffic_light_info))
        if crossing_info:
            all_info.append("Crossings: " + " | ".join(crossing_info))
        if parking_info:
            all_info.append("Parking: " + " | ".join(parking_info))
            
        # Join with newlines for better readability
        full_info = " | ".join(all_info)
        self.info_label.config(text=full_info)

    def stop(self):
        self.running = False
        self.status_label.config(text="Simulation Status: Stopped")
