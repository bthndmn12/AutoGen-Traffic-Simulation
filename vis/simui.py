import tkinter as tk
import asyncio
from tkinter import scrolledtext # <<< CHANGE: Import scrolledtext for easier scrollbars >>>

# ... (Keep the MapObject, RoadObject, ParkingAreaObject, VehicleObject,
#      TrafficLightObject, PedestrianCrossingObject classes as they were) ...
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
        
        # Adjust size based on parking type
        if parking_type == "roadside":
            self.width = 20  # Smaller width for roadside parking
            self.height = 15  # Smaller height for roadside parking
        else:
            self.width = width
            self.height = height
            
        self.parking_type = parking_type

    def render(self, canvas):
        if self.agent:
            # Determine color based on occupancy
            if hasattr(self.agent, 'is_full') and self.agent.is_full:
                fill_color = "red"
            elif hasattr(self.agent, 'current_occupancy') and hasattr(self.agent, 'capacity') and self.agent.capacity > 0:
                occupancy_ratio = self.agent.current_occupancy / self.agent.capacity
                if occupancy_ratio >= 0.7:
                    fill_color = "orange"
                else:
                    fill_color = "blue"
            else:
                fill_color = "blue" # Default or if capacity is 0

            # Adjust styling based on type
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
            elif self.parking_type == "roadside":
                # Draw roadside parking as a smaller blue box
                canvas.create_rectangle(
                    self.x - self.width/2, self.y - self.height/2,
                    self.x + self.width/2, self.y + self.height/2,
                    fill=fill_color, outline="black", width=1
                )
                # Add small dots to indicate parking spots
                spot_size = 2
                for i in range(-1, 2):
                    spot_x = self.x + (i * self.width/3)
                    canvas.create_rectangle(
                        spot_x - spot_size, self.y - spot_size,
                        spot_x + spot_size, self.y + spot_size,
                        fill="white", outline="white"
                    )
            else:
                # Draw street parking (rectangle with P symbol)
                canvas.create_rectangle(
                    self.x - self.width/2, self.y - self.height/2,
                    self.x + self.width/2, self.y + self.height/2,
                    fill=fill_color, outline="black", width=2
                )

            # Add parking symbol (smaller for roadside)
            font_size = 8 if self.parking_type == "roadside" else 12
            canvas.create_text(
                self.x, self.y,
                text="P",
                fill="white",
                font=("Arial", font_size, "bold")
            )

            # Add status text
            if hasattr(self.agent, 'current_occupancy') and hasattr(self.agent, 'capacity'):
                status_text = f"{self.id} ({self.agent.current_occupancy}/{self.agent.capacity})"
            else:
                status_text = self.id

            font_size = 7 if self.parking_type == "roadside" else 9
            text_offset = self.height/2 + 8 if self.parking_type == "roadside" else self.height/2 + 10
            canvas.create_text(
                self.x, self.y - text_offset,
                text=status_text,
                fill="black",
                font=("Arial", font_size)
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
        # Default wait_times if agent doesn't have it yet
        if self.agent and not hasattr(self.agent, 'wait_times'):
            self.agent.wait_times = [0]
        self.color_cycle = ["blue", "cyan", "navy", "purple"]


    def render(self, canvas):
        if self.agent:
            # Get position from agent, ensuring we convert any floats to integers for the canvas
            # We use self.x and self.y which already include the offset (set by the visualizer)
            position_x = int(self.x)
            position_y = int(self.y)

            # Determine vehicle color based on state and wait time
            color = "gray" # Default color
            if hasattr(self.agent, 'parking_state'):
                if self.agent.parking_state == "parked":
                    color = "darkgreen"
                elif self.agent.parking_state in ["parking", "exiting"]:
                    color = "darkblue"
                elif hasattr(self.agent, 'parked') and self.agent.parked: # Compatibility
                      color = "purple"
                elif hasattr(self.agent, 'wait_times'):
                      color = self.color_cycle[sum(self.agent.wait_times) % len(self.color_cycle)]
                else:
                      color = "blue" # Fallback driving color
            elif hasattr(self.agent, 'wait_times'): # If no parking_state, check wait_times
                 color = self.color_cycle[sum(self.agent.wait_times) % len(self.color_cycle)]

            # Draw a more visible vehicle
            canvas.create_rectangle(position_x - 10, position_y - 5, # Smaller rectangle
                                     position_x + 10, position_y + 5,
                                     fill=color, outline='black', width=1) # Thinner outline

            # Draw direction indicators (simple arrow shape based on road direction)
            # Check if driving and on a valid road segment
            is_driving = getattr(self.agent, 'parking_state', 'driving') == 'driving'
            has_roads = hasattr(self.agent, 'roads') and self.agent.roads
            current_pos_valid = hasattr(self.agent, 'current_position') and 0 <= self.agent.current_position < len(self.agent.roads)

            if is_driving and has_roads and current_pos_valid:
                road = self.agent.roads[self.agent.current_position]
                # Unpack coordinates, ensuring we handle tuple format robustly
                if isinstance(road, (list, tuple)) and len(road) >= 4:
                    x1, y1, x2, y2 = road[:4]

                    # Determine if road is more horizontal or vertical
                    dx, dy = 0, 0
                    arrow_len = 8 # Shorter arrow
                    if abs(x2 - x1) > abs(y2 - y1):  # Horizontal road
                        dx = arrow_len if x2 > x1 else -arrow_len
                    elif abs(y2 - y1) > abs(x2 - x1): # Vertical road
                        dy = arrow_len if y2 > y1 else -arrow_len
                    # Only draw arrow if direction is clear
                    if dx != 0 or dy != 0:
                         canvas.create_line(position_x, position_y, position_x + dx, position_y + dy,
                                            arrow="last", width=1, fill="white") # Thinner arrow

            # Draw the vehicle ID and position info
            status_info = ""
            if hasattr(self.agent, 'parking_state') and self.agent.parking_state != "driving":
                if self.agent.parking_state == "parked" and hasattr(self.agent, 'target_parking'):
                     status_info = f" (PARKED at {self.agent.target_parking})"
                else:
                     status_info = f" ({self.agent.parking_state.upper()})"
            elif hasattr(self.agent, 'movement_progress'):
                 status_info = f" ({int(self.agent.movement_progress*100)}%)"

            # Display agent's real coordinates, not the canvas-adjusted ones
            agent_real_x = int(getattr(self.agent, "x", 0))
            agent_real_y = int(getattr(self.agent, "y", 0))
            # Position text slightly above the smaller vehicle
            canvas.create_text(position_x, position_y - 12,
                               text=f"{self.id}{status_info}", # Simplified text ({agent_real_x},{agent_real_y}) removed for less clutter
                               fill="black", font=("Arial", 8, "bold"), anchor="center") # Smaller font, centered
        else:
            canvas.create_rectangle(self.x - 10, self.y - 5, # Smaller rectangle
                                     self.x + 10, self.y + 5,
                                     fill='gray', outline='black')
            canvas.create_text(self.x, self.y - 12, text=f"{self.id} (no agent)", font=("Arial", 8)) # Smaller font


class TrafficLightObject(MapObject):
    def __init__(self, id, agent, x=300, y=250):
        super().__init__(id, x, y)
        self.agent = agent

    def render(self, canvas):
        light_size = 8 # Smaller light
        if self.agent and hasattr(self.agent, 'state'):
            light_color = "green" if self.agent.state.upper() == "GREEN" else "red"
            # Draw smaller traffic light for better visibility
            canvas.create_oval(self.x - light_size, self.y - light_size,
                               self.x + light_size, self.y + light_size,
                               fill=light_color, outline='black', width=1) # Thinner outline
            canvas.create_text(self.x, self.y - light_size - 8, text=f"{self.id}", font=("Arial", 8)) # Smaller font
        else:
            canvas.create_oval(self.x - light_size, self.y - light_size,
                               self.x + light_size, self.y + light_size,
                               fill="gray", outline='black')
            canvas.create_text(self.x, self.y - light_size - 8, text=f"{self.id} (no agent)", font=("Arial", 8)) # Smaller font


class PedestrianCrossingObject(MapObject):
    def __init__(self, id, agent, x=320, y=270):
        super().__init__(id, x, y)
        self.agent = agent

    def render(self, canvas):
        cross_size = 10 # Smaller crossing box
        if self.agent and hasattr(self.agent, 'is_occupied'):
            color = "orange" if self.agent.is_occupied else "white"
            # Make crossing more visible
            canvas.create_rectangle(self.x - cross_size, self.y - cross_size,
                                      self.x + cross_size, self.y + cross_size,
                                      fill=color, outline='black', width=1) # Thinner outline
            # Add striped pattern for crosswalk
            if not self.agent.is_occupied:
                for i in range(-cross_size+2, cross_size-1, 4): # Adjust stripe spacing
                    canvas.create_line(self.x - cross_size, self.y + i,
                                       self.x + cross_size, self.y + i,
                                       fill="black", width=1) # Thinner stripes

            canvas.create_text(self.x, self.y - cross_size - 8, text=f"{self.id}", font=("Arial", 8)) # Smaller font
        else:
            canvas.create_rectangle(self.x - cross_size, self.y - cross_size,
                                      self.x + cross_size, self.y + cross_size,
                                      fill="gray", outline='black')
            canvas.create_text(self.x, self.y - cross_size - 8, text=f"{self.id} (no agent)", font=("Arial", 8)) # Smaller font

class TrafficSimulationVisualizer:
    # <<< CHANGE: Adjusted default width to accommodate side panels >>>
    def __init__(self, width=1200, height=700, info_panel_width=200):
        self.running = True
        self.objects = []  # List[MapObject]
        self.root = tk.Tk()
        self.root.title("Traffic Simulation Visualizer")

        # <<< CHANGE: Store info panel width >>>
        self.info_panel_width = info_panel_width
        # <<< CHANGE: Calculate canvas width based on total width and panels >>>
        self.canvas_width = width - (2 * info_panel_width)
        self.canvas_height = height - 100 # Adjusted height for title/status

        self.root.geometry(f"{width}x{height}")
        self.root.configure(bg="#f0f0f0")

        # Center the window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_cordinate = int((screen_width/2) - (width)/2)
        y_cordinate = int((screen_height/2) - (height)/2)
        self.root.geometry(f"+{x_cordinate}+{y_cordinate}")

        # Main frame for overall padding
        self.main_frame = tk.Frame(self.root, bg="#f0f0f0", padx=10, pady=10)
        self.main_frame.pack(fill="both", expand=True)

        # Title label
        self.title_label = tk.Label(
            self.main_frame,
            text="Traffic Simulation",
            font=("Arial", 16, "bold"),
            bg="#f0f0f0",
            fg="#333333"
        )
        self.title_label.pack(pady=(0, 10))

        # <<< CHANGE: Create a central frame to hold panels and canvas horizontally >>>
        self.content_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.content_frame.pack(fill="both", expand=True)

        # <<< CHANGE: Left Information Panel >>>
        self.left_info_frame = tk.Frame(self.content_frame, width=self.info_panel_width, bg="#e8e8e8", bd=1, relief="sunken")
        self.left_info_frame.pack(side="left", fill="y", padx=(0, 5))
        self.left_info_frame.pack_propagate(False) # Prevent frame from shrinking to content

        tk.Label(self.left_info_frame, text="Vehicles", font=("Arial", 11, "bold"), bg="#e8e8e8").pack(pady=5)
        self.left_info_text = scrolledtext.ScrolledText(
            self.left_info_frame,
            wrap=tk.WORD,
            font=("Arial", 9),
            bg="#ffffff",
            state="disabled" # Start read-only
        )
        self.left_info_text.pack(fill="both", expand=True, padx=5, pady=(0,5))

        # <<< CHANGE: Right Information Panel >>>
        self.right_info_frame = tk.Frame(self.content_frame, width=self.info_panel_width, bg="#e8e8e8", bd=1, relief="sunken")
        self.right_info_frame.pack(side="right", fill="y", padx=(5, 0))
        self.right_info_frame.pack_propagate(False) # Prevent frame from shrinking

        tk.Label(self.right_info_frame, text="Infrastructure", font=("Arial", 11, "bold"), bg="#e8e8e8").pack(pady=5)
        self.right_info_text = scrolledtext.ScrolledText(
            self.right_info_frame,
            wrap=tk.WORD,
            font=("Arial", 9),
            bg="#ffffff",
            state="disabled" # Start read-only
        )
        self.right_info_text.pack(fill="both", expand=True, padx=5, pady=(0,5))

        # <<< CHANGE: Canvas Frame (Packed in the middle) >>>
        self.canvas_frame = tk.Frame(
            self.content_frame, # Packed into the content_frame
            bg="#d0d0d0",
            highlightbackground="#a0a0a0",
            highlightthickness=1
        )
        # <<< CHANGE: Canvas Frame packed to expand and fill remaining space >>>
        self.canvas_frame.pack(side="left", fill="both", expand=True)

        # The actual canvas for drawing
        self.canvas = tk.Canvas(
            self.canvas_frame,
            # <<< CHANGE: Use calculated canvas dimensions >>>
            width=self.canvas_width,
            height=self.canvas_height,
            bg="white",
            highlightthickness=0
        )
        self.canvas.pack(padx=2, pady=2, fill="both", expand=True) # Canvas fills its frame

        # <<< CHANGE: Frame for status and controls at the bottom >>>
        self.bottom_frame = tk.Frame(self.main_frame, bg="#f0f0f0", pady=5)
        self.bottom_frame.pack(fill="x")

        # Status label
        self.status_label = tk.Label(
            self.bottom_frame, # Moved to bottom frame
            text="Simulation Status: Running",
            bg="#f0f0f0",
            fg="#333333",
            font=("Arial", 10)
        )
        self.status_label.pack(side="left", padx=5)

        # Control buttons frame (Example - you might have buttons here)
        self.control_frame = tk.Frame(self.bottom_frame, bg="#f0f0f0")
        self.control_frame.pack(side="right", padx=5)
        # Example button:
        # tk.Button(self.control_frame, text="Stop", command=self.stop).pack()

        # Dictionary to store road objects by ID
        self.road_objects = {}

        # Rendering offsets to center the map in the canvas
        # <<< CHANGE: Use canvas dimensions for centering >>>
        self.offset_x = self.canvas_width // 2
        self.offset_y = self.canvas_height // 2

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

        # Update map boundaries based on object position (using original coordinates)
        if isinstance(obj, RoadObject):
            self.min_x = min(self.min_x, obj.x1, obj.x2)
            self.max_x = max(self.max_x, obj.x1, obj.x2)
            self.min_y = min(self.min_y, obj.y1, obj.y2)
            self.max_y = max(self.max_y, obj.y1, obj.y2)
        elif hasattr(obj, 'x') and hasattr(obj, 'y'):
             # Use agent coords if available, otherwise object coords
            obj_x = getattr(obj.agent, 'x', obj.x) if hasattr(obj, 'agent') and obj.agent else obj.x
            obj_y = getattr(obj.agent, 'y', obj.y) if hasattr(obj, 'agent') and obj.agent else obj.y
            self.min_x = min(self.min_x, obj_x)
            self.max_x = max(self.max_x, obj_x)
            self.min_y = min(self.min_y, obj_y)
            self.max_y = max(self.max_y, obj_y)


        # Recalculate the center offset based on the object boundaries
        # <<< CHANGE: Use canvas dimensions for centering calculation >>>
        if self.min_x != float('inf') and self.max_x != float('-inf'):
            map_center_x = (self.min_x + self.max_x) / 2
            map_center_y = (self.min_y + self.max_y) / 2

            # Calculate offset to center the map within the canvas
            self.offset_x = self.canvas_width / 2 - map_center_x
            self.offset_y = self.canvas_height / 2 - map_center_y


    async def run(self):
        # Final calculation of the center before starting
        self._calculate_map_center()

        while self.running:
            # Update roads with current vehicle count
            self.update_road_vehicle_counts()

            # Clear and redraw everything
            self.canvas.delete("all")
            self.draw_background() # Draw background grid first

            # <<< CHANGE: Display offset relative to canvas >>>
            # Optional: display offset info
            # self.canvas.create_text(
            #    self.canvas_width/2, 15, # Adjusted position
            #    text=f"Offset: ({int(self.offset_x)}, {int(self.offset_y)})",
            #    fill="#666666",
            #    font=("Arial", 8)
            #)

            # Draw roads first, then other objects on top
            # Sort to draw roads first, then non-vehicles, then vehicles last
            def sort_key(obj):
                if isinstance(obj, RoadObject): return 0
                if isinstance(obj, VehicleObject): return 2
                return 1

            for obj in sorted(self.objects, key=sort_key):
                if isinstance(obj, RoadObject):
                    # Center road objects using calculated offset
                    obj_copy = RoadObject(
                        obj.x1 + self.offset_x, obj.y1 + self.offset_y,
                        obj.x2 + self.offset_x, obj.y2 + self.offset_y,
                        obj.base_color, obj.width, obj.capacity, obj.road_id
                    )
                    obj_copy.current_vehicles = obj.current_vehicles
                    obj_copy.render(self.canvas)
                elif isinstance(obj, MapObject):
                     # Use agent's position if available for vehicles
                     if isinstance(obj, VehicleObject) and obj.agent and hasattr(obj.agent, "x") and hasattr(obj.agent, "y"):
                         agent_x = obj.agent.x
                         agent_y = obj.agent.y
                     # Otherwise use the object's stored position
                     elif hasattr(obj, 'x') and hasattr(obj, 'y'):
                         agent_x = obj.x
                         agent_y = obj.y
                     else:
                         continue # Skip if no position

                     # Apply offset for rendering
                     render_x = agent_x + self.offset_x
                     render_y = agent_y + self.offset_y

                     # Create a temporary copy with offset coordinates for rendering
                     # This avoids modifying the original object's state
                     obj_class = obj.__class__
                     if isinstance(obj, VehicleObject):
                         temp_obj = obj_class(obj.id, obj.agent, x=render_x, y=render_y)
                     elif isinstance(obj, ParkingAreaObject):
                          temp_obj = obj_class(obj.id, obj.agent, x=render_x, y=render_y,
                                               width=obj.width, height=obj.height, parking_type=obj.parking_type)
                     elif isinstance(obj, (TrafficLightObject, PedestrianCrossingObject)):
                          temp_obj = obj_class(obj.id, obj.agent, x=render_x, y=render_y)
                     else: # Generic case if other MapObjects exist
                          temp_obj = obj_class(obj.id, x=render_x, y=render_y)
                          # Copy other relevant attributes if needed for rendering

                     temp_obj.render(self.canvas)


            # <<< CHANGE: Update the new info panels >>>
            self.update_info_panels()
            self.root.update()
            await asyncio.sleep(0.05) # Slightly faster update rate

        try:
           if self.root.winfo_exists():
              self.root.destroy()
        except tk.TclError:
            pass # Window already destroyed

    def _calculate_map_center(self):
        """Calculate the center of the map based on object positions"""
        if not self.objects:
            # <<< CHANGE: Use canvas dimensions for default center >>>
            self.offset_x = self.canvas_width // 2
            self.offset_y = self.canvas_height // 2
            return

        # Reset boundaries
        self.min_x, self.max_x = float('inf'), float('-inf')
        self.min_y, self.max_y = float('inf'), float('-inf')

        # Find the bounds of all objects (using original coordinates)
        for obj in self.objects:
            if isinstance(obj, RoadObject):
                self.min_x = min(self.min_x, obj.x1, obj.x2)
                self.max_x = max(self.max_x, obj.x1, obj.x2)
                self.min_y = min(self.min_y, obj.y1, obj.y2)
                self.max_y = max(self.max_y, obj.y1, obj.y2)
            elif hasattr(obj, 'x') and hasattr(obj, 'y'):
                # Use agent coords if available, otherwise object coords
                obj_x = getattr(obj.agent, 'x', obj.x) if hasattr(obj, 'agent') and obj.agent else obj.x
                obj_y = getattr(obj.agent, 'y', obj.y) if hasattr(obj, 'agent') and obj.agent else obj.y
                self.min_x = min(self.min_x, obj_x)
                self.max_x = max(self.max_x, obj_x)
                self.min_y = min(self.min_y, obj_y)
                self.max_y = max(self.max_y, obj_y)

        # Only calculate if we have valid bounds
        if self.min_x != float('inf') and self.max_x != float('-inf'):
            map_center_x = (self.min_x + self.max_x) / 2
            map_center_y = (self.min_y + self.max_y) / 2

            # <<< CHANGE: Calculate offset relative to canvas dimensions >>>
            self.offset_x = self.canvas_width / 2 - map_center_x
            self.offset_y = self.canvas_height / 2 - map_center_y

            print(f"Map centered at offset: ({self.offset_x:.2f}, {self.offset_y:.2f}) relative to map origin")
        else:
            # Fallback if bounds are still infinite (e.g., only non-positioned objects)
            self.offset_x = self.canvas_width // 2
            self.offset_y = self.canvas_height // 2


    def update_road_vehicle_counts(self):
        """Update the current vehicle count on each road segment"""
        # Reset all road counts
        for road_obj in self.road_objects.values():
            road_obj.current_vehicles = 0

        # Count vehicles on each road
        for obj in self.objects:
            if isinstance(obj, VehicleObject) and obj.agent:
                 # Check if the vehicle is currently driving
                 is_driving = getattr(obj.agent, 'parking_state', 'driving') == 'driving'
                 has_roads = hasattr(obj.agent, 'roads') and obj.agent.roads
                 current_pos_valid = hasattr(obj.agent, 'current_position') and 0 <= obj.agent.current_position < len(obj.agent.roads)

                 if is_driving and has_roads and current_pos_valid:
                      road_tuple = obj.agent.roads[obj.agent.current_position]
                      # Check if road_tuple has enough elements for road_id (assuming it's the 6th element, index 5)
                      if isinstance(road_tuple, (list, tuple)) and len(road_tuple) >= 6:
                          road_id = road_tuple[5]
                          if road_id in self.road_objects:
                              self.road_objects[road_id].current_vehicles += 1


    def draw_background(self):
        # Draw a cleaner grid with lighter colors based on canvas dimensions
        grid_spacing = 50 # Smaller grid spacing
        # <<< CHANGE: Use canvas dimensions for grid lines >>>
        for i in range(0, int(self.canvas_width + grid_spacing), grid_spacing):
             # Draw vertical lines slightly dimmed
             self.canvas.create_line(i, 0, i, self.canvas_height, fill="#e8e8e8", dash=(2, 4))
             # Optional: Add coordinate text if needed, adjust position
             # self.canvas.create_text(i, 10, text=str(i - int(self.offset_x)), fill="#b0b0b0", font=("Arial", 7), anchor='n')

        for i in range(0, int(self.canvas_height + grid_spacing), grid_spacing):
             # Draw horizontal lines slightly dimmed
             self.canvas.create_line(0, i, self.canvas_width, i, fill="#e8e8e8", dash=(2, 4))
             # Optional: Add coordinate text if needed, adjust position
             # self.canvas.create_text(10, i, text=str(i - int(self.offset_y)), fill="#b0b0b0", font=("Arial", 7), anchor='w')


    # <<< CHANGE: Renamed and modified function to update side panels >>>
    def update_info_panels(self):
        vehicle_lines = []
        parking_lines = []
        light_lines = []
        crossing_lines = []
        road_lines = [] # <<< CHANGE: Added Road Info >>>

        # Collect information by category
        for obj in self.objects:
            if isinstance(obj, VehicleObject) and obj.agent:
                status_info = ""
                parking_state = getattr(obj.agent, 'parking_state', None)
                if parking_state and parking_state != "driving":
                     status_info = f" [{parking_state.upper()}]"
                     target_parking = getattr(obj.agent, 'target_parking', None)
                     if parking_state == "parked" and target_parking:
                          status_info += f" at {target_parking}"
                elif hasattr(obj.agent, 'movement_progress'):
                     status_info = f" ({int(obj.agent.movement_progress*100)}% move)"


                road_info = ""
                if parking_state == "driving" and hasattr(obj.agent, 'current_position') and hasattr(obj.agent, 'roads') and obj.agent.roads and 0 <= obj.agent.current_position < len(obj.agent.roads):
                    road_tuple = obj.agent.roads[obj.agent.current_position]
                    if isinstance(road_tuple, (list, tuple)) and len(road_tuple) >= 6:
                        road_id = road_tuple[5]
                        road_info = f" on {road_id}"

                target_info = ""
                target_parking = getattr(obj.agent, 'target_parking', None)
                if target_parking and parking_state == "driving":
                    target_info = f" -> {target_parking}"

                # Use real agent coordinates
                real_x = int(getattr(obj.agent, "x", 0))
                real_y = int(getattr(obj.agent, "y", 0))

                vehicle_lines.append(f"{obj.id}: ({real_x},{real_y}){status_info}{road_info}{target_info}")

            elif isinstance(obj, ParkingAreaObject) and obj.agent:
                if hasattr(obj.agent, 'current_occupancy') and hasattr(obj.agent, 'capacity'):
                    capacity_info = f" ({obj.agent.current_occupancy}/{obj.agent.capacity})"
                    state = " [FULL]" if getattr(obj.agent, 'is_full', False) else ""
                    parking_lines.append(f"{obj.id} ({obj.parking_type}){capacity_info}{state}")
                else:
                     parking_lines.append(f"{obj.id} ({obj.parking_type}) [No Cap Info]")

            elif isinstance(obj, TrafficLightObject) and obj.agent:
                if hasattr(obj.agent, 'state'):
                    light_lines.append(f"{obj.id}: {obj.agent.state.upper()}")
                else:
                    light_lines.append(f"{obj.id}: [No State]")

            elif isinstance(obj, PedestrianCrossingObject) and obj.agent:
                 if hasattr(obj.agent, 'is_occupied'):
                    status = "OCCUPIED" if obj.agent.is_occupied else "FREE"
                    crossing_lines.append(f"{obj.id}: {status}")
                 else:
                     crossing_lines.append(f"{obj.id}: [No State]")

            # <<< CHANGE: Collect Road Info >>>
            elif isinstance(obj, RoadObject) and obj.road_id:
                color_state = ""
                if obj.current_color == "orange": color_state = "[FULL]"
                elif obj.current_color == "yellow": color_state = "[BUSY]"
                road_lines.append(f"{obj.road_id}: {obj.current_vehicles}/{obj.capacity} {color_state}")


        # Update Left Panel (Vehicles)
        self.left_info_text.config(state="normal") # Enable writing
        self.left_info_text.delete('1.0', tk.END) # Clear previous content
        if vehicle_lines:
            self.left_info_text.insert(tk.END, "\n".join(sorted(vehicle_lines)))
        else:
            self.left_info_text.insert(tk.END, "(No vehicles)")
        self.left_info_text.config(state="disabled") # Disable writing

        # Update Right Panel (Infrastructure)
        current_yview = self.right_info_text.yview()
        self.right_info_text.config(state="normal") # Enable writing
        self.right_info_text.delete('1.0', tk.END) # Clear previous content

        if road_lines:
             self.right_info_text.insert(tk.END, "--- Roads ---\n")
             self.right_info_text.insert(tk.END, "\n".join(sorted(road_lines)) + "\n\n")
        if parking_lines:
            self.right_info_text.insert(tk.END, "--- Parking ---\n")
            self.right_info_text.insert(tk.END, "\n".join(sorted(parking_lines)) + "\n\n")
        if light_lines:
             self.right_info_text.insert(tk.END, "--- Traffic Lights ---\n")
             self.right_info_text.insert(tk.END, "\n".join(sorted(light_lines)) + "\n\n")
        if crossing_lines:
            self.right_info_text.insert(tk.END, "--- Crossings ---\n")
            self.right_info_text.insert(tk.END, "\n".join(sorted(crossing_lines)) + "\n\n")

        if not any([road_lines, parking_lines, light_lines, crossing_lines]):
             self.right_info_text.insert(tk.END, "(No infrastructure data)")

        self.right_info_text.yview_moveto(current_yview[0])
        self.right_info_text.config(state="disabled") # Disable writing


    def stop(self):
        self.running = False
        self.status_label.config(text="Simulation Status: Stopped")


# Example usage (if you want to run this file standalone for testing UI)
async def main():
    vis = TrafficSimulationVisualizer(width=1200, height=700)

    # --- Add some dummy objects for UI testing ---
    # Dummy agent classes (replace with your actual agents)
    class DummyAgent: pass
    class DummyVehicleAgent(DummyAgent): x, y, wait_times, parking_state, current_position, roads, movement_progress, target_parking = 50, 50, [0], "driving", 0, [('R1', 0,0,100,100, 2, 'R1')], 0.5, "P1"
    class DummyParkingAgent(DummyAgent): current_occupancy, capacity, is_full = 1, 5, False
    class DummyTLAgent(DummyAgent): state = "GREEN"
    class DummyCrossingAgent(DummyAgent): is_occupied = False

    # Add roads
    vis.add_object(RoadObject(0, 0, 200, 0, road_id="R1", capacity=3))
    vis.add_object(RoadObject(200, 0, 200, 200, road_id="R2", capacity=2))
    vis.add_object(RoadObject(0, 0, 0, 200, road_id="R3", capacity=2))
    vis.add_object(RoadObject(0, 200, 200, 200, road_id="R4", capacity=4))

    # Add parking
    vis.add_object(ParkingAreaObject("P1", DummyParkingAgent(), x=250, y=50, parking_type="street"))
    vis.add_object(ParkingAreaObject("P2", DummyParkingAgent(), x=50, y=250, parking_type="building"))

    # Add traffic control
    vis.add_object(TrafficLightObject("TL1", DummyTLAgent(), x=200, y=-10))
    vis.add_object(PedestrianCrossingObject("PC1", DummyCrossingAgent(), x=100, y=200))

    # Add vehicles
    veh1_agent = DummyVehicleAgent()
    vis.add_object(VehicleObject("V1", veh1_agent))

    veh2_agent = DummyVehicleAgent()
    veh2_agent.x, veh2_agent.y = 10, 150
    veh2_agent.roads = [('R3', 0,0,0,200, 2, 'R3')] # Example road for V2
    veh2_agent.parking_state = "driving"
    veh2_agent.target_parking = "P2"
    vis.add_object(VehicleObject("V2", veh2_agent))

    veh3_agent = DummyVehicleAgent()
    veh3_agent.x, veh3_agent.y = 250, 50
    veh3_agent.parking_state = "parked"
    veh3_agent.target_parking = "P1"
    vis.add_object(VehicleObject("V3", veh3_agent))
    # --- End dummy objects ---

    # Example: Simulate vehicle movement and state changes (in a real scenario, agents update this)
    async def update_dummies():
        import random
        count = 0
        while vis.running:
            await asyncio.sleep(1) # Update dummies less frequently than UI refresh
            count += 1
            # Move V1
            if veh1_agent.parking_state == "driving":
                 veh1_agent.x = (veh1_agent.x + 10) % 200
                 veh1_agent.movement_progress = (veh1_agent.x / 200)
                 if veh1_agent.x > 190: # Simulate reaching end of R1
                     veh1_agent.current_position = 1 # Move to R2 (index 1 assumed)
                     veh1_agent.roads = [('R1', 0,0,200,0, 2, 'R1'), ('R2', 200,0,200,200, 2, 'R2')] # Update roads list
                     veh1_agent.x, veh1_agent.y = 200, 0 # Start pos of R2

            # Randomly change TL1 state
            if count % 5 == 0:
                 DummyTLAgent.state = random.choice(["GREEN", "RED"])

            # Randomly occupy crossing
            if count % 7 == 0:
                 DummyCrossingAgent.is_occupied = not DummyCrossingAgent.is_occupied

            # Fill P1
            if count % 10 == 0 and DummyParkingAgent.current_occupancy < DummyParkingAgent.capacity:
                 DummyParkingAgent.current_occupancy += 1
                 DummyParkingAgent.is_full = (DummyParkingAgent.current_occupancy == DummyParkingAgent.capacity)


    # Run the visualizer and the dummy update concurrently
    try:
        await asyncio.gather(
            vis.run(),
            update_dummies()
        )
    except tk.TclError:
        print("Tkinter window closed.")
    except asyncio.CancelledError:
        print("Simulation tasks cancelled.")
    finally:
        vis.stop() # Ensure running flag is false


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Simulation interrupted by user.")