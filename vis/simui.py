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
        self.color = color
        self.width = width
        self.capacity = capacity
        self.road_id = road_id
        self.current_vehicles = 0  # Track current number of vehicles on road

    def render(self, canvas):
        # Adjust color based on capacity utilization
        road_color = self.color
        if hasattr(self, 'current_vehicles') and self.capacity > 0:
            if self.current_vehicles >= self.capacity:
                road_color = "red"  # Road at or over capacity
            elif self.current_vehicles >= self.capacity * 0.7:
                road_color = "orange"  # Road approaching capacity
        
        canvas.create_line(self.x1, self.y1, self.x2, self.y2, fill=road_color, width=self.width)
        
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
    def __init__(self, id, agent, x=50, y=290):
        super().__init__(id, x, y)
        self.agent = agent
        self.color_cycle = ["blue", "cyan", "navy", "purple"]

    def render(self, canvas):
        if self.agent:
            # Get position from agent, ensuring we convert any floats to integers for the canvas
            position_x = int(getattr(self.agent, "x", self.x))
            position_y = int(getattr(self.agent, "y", self.y))
            
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
                
            canvas.create_text(position_x, position_y - 25, 
                              text=f"{self.id} ({position_x}, {position_y}){status_info}",
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
    def __init__(self, width=800, height=600):
        self.running = True
        self.objects = []  # List[MapObject]
        self.root = tk.Tk()
        self.root.title("Traffic Simulation Visualizer")
        self.canvas = tk.Canvas(self.root, width=width, height=height, bg="white")
        self.canvas.pack()
        self.info_label = tk.Label(self.root, text="")
        self.info_label.pack()
        self.width = width
        self.height = height
        self.road_objects = {}  # Dictionary to store road objects by ID

    def add_object(self, obj):
        print(f"Added object: {getattr(obj, 'id', obj.__class__.__name__)}")
        self.objects.append(obj)
        
        # Store road objects in a dictionary for quick lookup
        if isinstance(obj, RoadObject) and obj.road_id:
            self.road_objects[obj.road_id] = obj

    async def run(self):
        while self.running:
            # Update roads with current vehicle count
            self.update_road_vehicle_counts()
            
            # Clear and redraw everything
            self.canvas.delete("all")
            self.draw_background()
            
            # Draw roads first, then other objects on top
            for obj in sorted(self.objects, key=lambda x: not isinstance(x, RoadObject)):
                obj.render(self.canvas)

            self.update_info_label()
            self.root.update()
            await asyncio.sleep(0.1)
        self.root.destroy()

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
        # Draw grid lines for reference
        for i in range(0, self.width, 100):
            self.canvas.create_line(i, 0, i, self.height, fill="lightgray", dash=(4, 4))
            self.canvas.create_text(i, 10, text=str(i), fill="gray")
        
        for i in range(0, self.height, 100):
            self.canvas.create_line(0, i, self.width, i, fill="lightgray", dash=(4, 4))
            self.canvas.create_text(10, i, text=str(i), fill="gray")

    def update_info_label(self):
        info_texts = []
        
        # Vehicle information
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
                        
                parking_info = ""
                if hasattr(obj.agent, 'target_parking') and obj.agent.target_parking:
                    parking_info = f" → {obj.agent.target_parking}"
                    
                info_texts.append(f"Vehicle {obj.id}: Pos {obj.agent.current_position}{status_info}{road_info}{parking_info}")
                
            # Traffic light information
            elif isinstance(obj, TrafficLightObject) and obj.agent:
                info_texts.append(f"Light {obj.id}: {obj.agent.state}")
                
            # Pedestrian crossing information
            elif isinstance(obj, PedestrianCrossingObject) and obj.agent:
                status = "occupied" if obj.agent.is_occupied else "free"
                info_texts.append(f"Crossing {obj.id}: {status}")
                
            # Parking area information
            elif isinstance(obj, ParkingAreaObject) and obj.agent:
                capacity_info = f" ({obj.agent.current_occupancy}/{obj.agent.capacity})"
                info_texts.append(f"Parking {obj.id}{capacity_info}")

        self.info_label.config(text=" | ".join(info_texts))

    def stop(self):
        self.running = False
