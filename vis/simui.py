import tkinter as tk
from tkinter import ttk
import asyncio
from tkinter import scrolledtext
import math

# Define some basic styling constants
BG_COLOR = "#f0f0f0"
PANEL_BG = "#e0e0e0"
CANVAS_BG = "white"
TEXT_COLOR = "#333333"
TITLE_FONT = ("Arial", 16, "bold")
LABEL_FONT = ("Arial", 11, "bold")
INFO_FONT = ("Arial", 9)
STATUS_FONT = ("Arial", 10)

class MapObject:
    def __init__(self, id, x, y):
        self.id = id
        self.x = x
        self.y = y

    def render(self, canvas, scale_func, zoom_level):  # Add zoom_level parameter
        raise NotImplementedError("Subclasses should implement render method")

class RoadObject:
    def __init__(self, x1, y1, x2, y2, color="gray", width=20, capacity=2, road_id=None):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.base_color = color
        self.current_color = color
        self.width = width
        self.capacity = capacity
        self.road_id = road_id
        self.current_vehicles = 0

    def render(self, canvas, scale_func, zoom_level):  # Add zoom_level parameter
        sx1, sy1 = scale_func(self.x1, self.y1)
        sx2, sy2 = scale_func(self.x2, self.y2)
        scaled_width = max(1, self.width * zoom_level)

        if self.base_color != "red":
            self.current_color = self.base_color
            if hasattr(self, 'current_vehicles') and self.capacity > 0:
                if self.current_vehicles >= self.capacity:
                    self.current_color = "orange"
                elif self.current_vehicles >= self.capacity * 0.7:
                    self.current_color = "yellow"
        else:
            self.current_color = self.base_color

        canvas.create_line(sx1, sy1, sx2, sy2, fill=self.current_color, width=max(3, scaled_width * 0.8))

        marker_size = max(1, 3 * zoom_level)
        canvas.create_oval(sx1-marker_size, sy1-marker_size, sx1+marker_size, sy1+marker_size, fill="black", outline="")
        canvas.create_oval(sx2-marker_size, sy2-marker_size, sx2+marker_size, sy2+marker_size, fill="black", outline="")

        if self.road_id:
            mid_x = sx1 + (sx2 - sx1) / 2
            mid_y = sy1 + (sy2 - sy1) / 2
            capacity_text = f"{self.road_id} ({self.current_vehicles}/{self.capacity})"
            font_size = max(6, int(8 * zoom_level**0.5))
            canvas.create_text(mid_x, mid_y - max(5, 10 * zoom_level), text=capacity_text, fill="black", font=("Arial", font_size))

class ParkingAreaObject(MapObject):
    def __init__(self, id, agent, x=200, y=200, width=40, height=30, parking_type="street"):
        super().__init__(id, x, y)
        self.agent = agent
        self.width = width
        self.height = height
        self.parking_type = parking_type

    def render(self, canvas, scale_func, zoom_level):  # Add zoom_level parameter
        sx, sy = scale_func(self.x, self.y)
        zoom = zoom_level

        if self.agent:
            if hasattr(self.agent, 'is_full') and self.agent.is_full:
                fill_color = "#e74c3c"
            elif hasattr(self.agent, 'current_occupancy') and hasattr(self.agent, 'capacity') and self.agent.capacity > 0:
                occupancy_ratio = self.agent.current_occupancy / self.agent.capacity
                if occupancy_ratio >= 0.7:
                    fill_color = "#f39c12"
                else:
                    fill_color = "#3498db"
            else:
                fill_color = "#3498db"

            outline_color = "#555555"
            text_fill = "white"

            if self.parking_type == "building":
                base_w, base_h = self.width * 1.5, self.height * 1.5
                width = max(10, base_w * zoom**0.7)
                height = max(8, base_h * zoom**0.7)
                canvas.create_rectangle(
                    sx - width/2, sy - height/2, sx + width/2, sy + height/2,
                    fill=fill_color, outline=outline_color, width=1
                )
                roof_h = max(3, 10 * zoom**0.7)
                canvas.create_polygon(
                    sx - width/2, sy - height/2, sx, sy - height/2 - roof_h,
                    sx + width/2, sy - height/2,
                    fill="#2980b9", outline=outline_color
                )
            elif self.parking_type == "roadside" or self.parking_type == "street":
                base_w, base_h = self.width * 0.7, self.height * 0.7
                width = max(5, base_w * zoom)
                height = max(4, base_h * zoom)
                canvas.create_rectangle(
                    sx - width/2, sy - height/2, sx + width/2, sy + height/2,
                    fill=fill_color, outline=outline_color, width=1
                )
                if self.parking_type == "roadside":
                    canvas.create_line(sx - width/2 + 2, sy, sx + width/2 - 2, sy, fill=text_fill, width=1, dash=(2,2))

            base_font_size = 8 if self.parking_type == "roadside" else 10
            font_size = max(5, int(base_font_size * zoom**0.6))
            canvas.create_text(sx, sy, text="P", fill=text_fill, font=("Arial", font_size, "bold"))

            if hasattr(self.agent, 'current_occupancy') and hasattr(self.agent, 'capacity'):
                status_text = f"{self.id} ({self.agent.current_occupancy}/{self.agent.capacity})"
            else:
                status_text = self.id

            base_font_size_status = 7 if self.parking_type == "roadside" else 8
            font_size_status = max(5, int(base_font_size_status * zoom**0.6))
            base_offset = self.height/2 + 6 if self.parking_type == "roadside" else self.height/2 + 8
            text_offset = max(4, base_offset * zoom)
            canvas.create_text(sx, sy - text_offset, text=status_text, fill=TEXT_COLOR, font=("Arial", font_size_status))
        else:
            width = max(8, self.width * zoom)
            height = max(6, self.height * zoom)
            canvas.create_rectangle(
                sx - width/2, sy - height/2, sx + width/2, sy + height/2,
                fill="gray", outline="#555555"
            )
            font_size = max(5, int(8 * zoom**0.6))
            text_offset = max(4, (self.height/2 + 8) * zoom)
            canvas.create_text(sx, sy - text_offset, text=f"{self.id} (no agent)", font=("Arial", font_size))

class VehicleObject(MapObject):
    def __init__(self, id, agent, x=50, y=300):
        super().__init__(id, x, y)
        self.agent = agent
        self.render_x = None
        self.render_y = None

    def render(self, canvas, render_x, render_y, scale_func, zoom_level):  # Add zoom_level parameter
        zoom = zoom_level
        if self.agent:
            position_x = int(render_x)
            position_y = int(render_y)

            color = "#bdc3c7"
            outline_color = "#2c3e50"
            if hasattr(self.agent, 'parking_state'):
                if self.agent.parking_state == "parked":
                    color = "#27ae60"
                elif self.agent.parking_state in ["parking", "exiting"]:
                    color = "#2980b9"
                elif hasattr(self.agent, 'parked') and self.agent.parked:
                    color = "#8e44ad"
                elif hasattr(self.agent, 'wait_times') and sum(self.agent.wait_times) > 0:
                    wait_level = min(sum(self.agent.wait_times), 5)
                    if wait_level > 2:
                        color = "#f39c12"
                    else:
                        color = "#f1c40f"
                else:
                    color = "#3498db"

            base_half_width = 10
            base_half_height = 5
            half_width = max(4, base_half_width * zoom)
            half_height = max(2, base_half_height * zoom)
            radius = max(1, 4 * zoom)

            points = [position_x - half_width, position_y - half_height + radius,
                      position_x - half_width + radius, position_y - half_height,
                      position_x + half_width - radius, position_y - half_height,
                      position_x + half_width, position_y - half_height + radius,
                      position_x + half_width, position_y + half_height - radius,
                      position_x + half_width - radius, position_y + half_height,
                      position_x - half_width + radius, position_y + half_height,
                      position_x - half_width, position_y + half_height - radius]
            canvas.create_polygon(points, fill=color, outline=outline_color, smooth=True, width=1)

            is_driving = getattr(self.agent, 'parking_state', 'driving') == 'driving'
            has_roads = hasattr(self.agent, 'roads') and self.agent.roads
            current_pos_valid = hasattr(self.agent, 'current_position') and 0 <= self.agent.current_position < len(self.agent.roads)

            if is_driving and has_roads and current_pos_valid:
                road = self.agent.roads[self.agent.current_position]
                if isinstance(road, (list, tuple)) and len(road) >= 4:
                    sx1, sy1 = scale_func(road[0], road[1])
                    sx2, sy2 = scale_func(road[2], road[3])

                    dx, dy = 0, 0
                    arrow_len = max(2, 5 * zoom)
                    if abs(sx2 - sx1) > abs(sy2 - sy1):
                        dx = arrow_len if sx2 > sx1 else -arrow_len
                    elif abs(sy2 - sy1) > abs(sx1 - sx2):
                        dy = arrow_len if sy2 > sy1 else -arrow_len
                    if abs(sx2 - sx1) < 0.1 and abs(sy2 - sy1) < 0.1:
                        dx, dy = 0, 0

                    if dx != 0 or dy != 0:
                        p1 = (position_x + dx, position_y + dy)
                        p2 = (position_x + (dy/2), position_y - (dx/2))
                        p3 = (position_x - (dy/2), position_y + (dx/2))
                        canvas.create_polygon(p1, p2, p3, fill="white", outline="")

            status_info = ""
            if hasattr(self.agent, 'parking_state') and self.agent.parking_state != "driving":
                status_info = f" [{self.agent.parking_state[:4].upper()}]"

            font_size = max(5, int(7 * zoom**0.6))
            canvas.create_text(position_x, position_y,
                               text=f"{self.id}{status_info}",
                               fill=outline_color, font=("Arial", font_size, "bold"), anchor="center")
        else:
            half_width = max(4, 10 * zoom)
            half_height = max(2, 5 * zoom)
            canvas.create_rectangle(render_x - half_width, render_y - half_height, render_x + half_width, render_y + half_height,
                                     fill='gray', outline='black')
            font_size = max(5, int(7 * zoom**0.6))
            canvas.create_text(render_x, render_y, text=f"{self.id}", font=("Arial", font_size))

class TrafficLightObject(MapObject):
    def __init__(self, id, agent, x=300, y=250):
        super().__init__(id, x, y)
        self.agent = agent

    def render(self, canvas, scale_func, zoom_level):  # Add zoom_level parameter
        sx, sy = scale_func(self.x, self.y)
        zoom = zoom_level
        light_size = max(2, 6 * zoom)
        outline_color = "#555555"
        if self.agent and hasattr(self.agent, 'state'):
            light_color = "#2ecc71" if self.agent.state.upper() == "GREEN" else "#e74c3c"
            canvas.create_oval(sx - light_size, sy - light_size,
                               sx + light_size, sy + light_size,
                               fill=light_color, outline=outline_color, width=1)
            post_height = max(2, 5 * zoom)
            canvas.create_line(sx, sy + light_size, sx, sy + light_size + post_height, fill=outline_color)
            font_size = max(5, int(7 * zoom**0.6))
            text_offset = max(3, (light_size + 6) * zoom)
            canvas.create_text(sx, sy - text_offset, text=f"{self.id}", font=("Arial", font_size), fill=TEXT_COLOR)
        else:
            canvas.create_oval(sx - light_size, sy - light_size,
                               sx + light_size, sy + light_size,
                               fill="gray", outline=outline_color)
            font_size = max(5, int(7 * zoom**0.6))
            text_offset = max(3, (light_size + 6) * zoom)
            canvas.create_text(sx, sy - text_offset, text=f"{self.id} (no agent)", font=("Arial", font_size), fill=TEXT_COLOR)

class PedestrianCrossingObject(MapObject):
    def __init__(self, id, agent, x=320, y=270):
        super().__init__(id, x, y)
        self.agent = agent

    def render(self, canvas, scale_func, zoom_level):  # Add zoom_level parameter
        sx, sy = scale_func(self.x, self.y)
        zoom = zoom_level
        cross_size = max(3, 8 * zoom)
        outline_color = "#555555"
        if self.agent and hasattr(self.agent, 'is_occupied'):
            color = "#f39c12" if self.agent.is_occupied else "#ecf0f1"
            canvas.create_rectangle(sx - cross_size, sy - cross_size,
                                      sx + cross_size, sy + cross_size,
                                      fill=color, outline=outline_color, width=1)
            if not self.agent.is_occupied:
                stripe_width = max(1, 3 * zoom)
                num_stripes = int((2 * cross_size) / (stripe_width * 2))
                for i in range(num_stripes):
                    stripe_x = sx - cross_size + stripe_width/2 + i * stripe_width * 2
                    canvas.create_line(stripe_x, sy - cross_size,
                                       stripe_x, sy + cross_size,
                                       fill="white", width=stripe_width)

            font_size = max(5, int(7 * zoom**0.6))
            text_offset = max(3, (cross_size + 6) * zoom)
            canvas.create_text(sx, sy - text_offset, text=f"{self.id}", font=("Arial", font_size), fill=TEXT_COLOR)
        else:
            canvas.create_rectangle(sx - cross_size, sy - cross_size,
                                      sx + cross_size, sy + cross_size,
                                      fill="gray", outline=outline_color)
            font_size = max(5, int(7 * zoom**0.6))
            text_offset = max(3, (cross_size + 6) * zoom)
            canvas.create_text(sx, sy - text_offset, text=f"{self.id} (no agent)", font=("Arial", font_size), fill=TEXT_COLOR)

class TrafficSimulationVisualizer:
    def __init__(self, width=1300, height=750, info_panel_width=250):
        print("Vis __init__: Start")
        self.running = True
        self.objects = []
        print("Vis __init__: Creating root window")
        self.root = tk.Tk()
        self.root.title("Traffic Simulation")
        self.root.configure(bg=BG_COLOR)
        print("Vis __init__: Configuring styles")
        style = ttk.Style(self.root)
        style.theme_use('clam')

        style.configure("TFrame", background=BG_COLOR)
        style.configure("Info.TFrame", background=PANEL_BG, borderwidth=1, relief="groove")
        style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=LABEL_FONT)
        style.configure("Title.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=TITLE_FONT)
        style.configure("Status.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=STATUS_FONT)
        style.configure("InfoTitle.TLabel", background=PANEL_BG, foreground=TEXT_COLOR, font=LABEL_FONT)

        self.info_panel_width = info_panel_width
        self.canvas_height = height - 100

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_cordinate = int((screen_width/2) - (width)/2)
        y_cordinate = int((screen_height/2) - (height)/2)
        self.root.geometry(f"{width}x{height}+{x_cordinate}+{y_cordinate}")

        print("Vis __init__: Setting up grid layout")
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.title_label = ttk.Label(self.root, text="Traffic Simulation", style="Title.TLabel", anchor="center")
        self.title_label.grid(row=0, column=0, columnspan=3, pady=(10, 5), sticky="ew")

        self.content_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.content_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)

        self.left_info_frame = ttk.Frame(self.content_frame, width=self.info_panel_width, style="Info.TFrame")
        self.left_info_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 5))
        self.left_info_frame.grid_propagate(False)
        self.left_info_frame.grid_rowconfigure(1, weight=1)
        self.left_info_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(self.left_info_frame, text="Vehicles", style="InfoTitle.TLabel", anchor="center").grid(row=0, column=0, pady=5, sticky="ew")
        self.left_info_text = scrolledtext.ScrolledText(
            self.left_info_frame, wrap=tk.WORD, font=INFO_FONT, bg="#ffffff", relief="flat",
            borderwidth=0, state="disabled", padx=5, pady=5
        )
        self.left_info_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0,5))

        self.canvas_frame = tk.Frame(self.content_frame, bg="#a0a0a0", bd=1, relief="sunken")
        self.canvas_frame.grid(row=0, column=1, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        print("Vis __init__: Creating canvas")
        self.canvas = tk.Canvas(self.canvas_frame, bg=CANVAS_BG, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.canvas_width = 1
        self.canvas_height = 1

        self.right_info_frame = ttk.Frame(self.content_frame, width=self.info_panel_width, style="Info.TFrame")
        self.right_info_frame.grid(row=0, column=2, sticky="nse", padx=(5, 0))
        self.right_info_frame.grid_propagate(False)
        self.right_info_frame.grid_rowconfigure(1, weight=1)
        self.right_info_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(self.right_info_frame, text="Infrastructure", style="InfoTitle.TLabel", anchor="center").grid(row=0, column=0, pady=5, sticky="ew")
        self.right_info_text = scrolledtext.ScrolledText(
            self.right_info_frame, wrap=tk.WORD, font=INFO_FONT, bg="#ffffff", relief="flat",
            borderwidth=0, state="disabled", padx=5, pady=5
        )
        self.right_info_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0,5))

        self.bottom_frame = ttk.Frame(self.root, style="TFrame", height=30)
        self.bottom_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(5, 10))
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ttk.Label(self.bottom_frame, text="Simulation Status: Initializing...", style="Status.TLabel")
        self.status_label.grid(row=0, column=0, sticky="w", padx=5)

        print("Vis __init__: Initializing attributes (zoom, pan, etc.)")
        self.road_objects = {}
        self.offset_x = 0
        self.offset_y = 0
        self.logical_center_x = 0
        self.logical_center_y = 0
        self.min_x, self.max_x = float('inf'), float('-inf')
        self.min_y, self.max_y = float('inf'), float('-inf')
        self.zoom_level = 1.0
        self.zoom_step = 1.2
        self.min_zoom = 0.1
        self.max_zoom = 5.0

        self.canvas.bind("<ButtonPress-1>", self._pan_start_left)
        self.canvas.bind("<B1-Motion>", self._pan_move_left)
        self.canvas.bind("<ButtonRelease-1>", self._pan_end_left)

        print("Vis __init__: Binding events")
        self.root.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)

        self._pan_start_x = 0
        self._pan_start_y = 0
        self._pan_last_offset_x = 0
        self._pan_last_offset_y = 0
        self.canvas.bind("<ButtonPress-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_move)
        self.canvas.bind("<ButtonRelease-2>", self._pan_end)
        print("Vis __init__: End")

    def _pan_start(self, event):
        self.canvas.config(cursor="fleur")
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._pan_last_offset_x = self.offset_x
        self._pan_last_offset_y = self.offset_y

    def _pan_move(self, event):
        dx = event.x - self._pan_start_x
        dy = event.y - self._pan_start_y
        self.offset_x = self._pan_last_offset_x + dx
        self.offset_y = self._pan_last_offset_y + dy

    def _pan_start_left(self, event):
        self.canvas.config(cursor="fleur")
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._pan_last_offset_x = self.offset_x
        self._pan_last_offset_y = self.offset_y

    def _pan_move_left(self, event):
        dx = event.x - self._pan_start_x
        dy = event.y - self._pan_start_y
        self.offset_x = self._pan_last_offset_x + dx
        self.offset_y = self._pan_last_offset_y + dy

    def _pan_end_left(self, event):
        self.canvas.config(cursor="")

    def _pan_end(self, event):
        self.canvas.config(cursor="")

    def _on_mouse_wheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.zoom_out(event.x, event.y)
        elif event.num == 4 or event.delta > 0:
            self.zoom_in(event.x, event.y)

    def _zoom(self, factor, mouse_x, mouse_y):
        new_zoom = self.zoom_level * factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))

        if new_zoom == self.zoom_level:
            return

        logical_mouse_x = self.logical_center_x + (mouse_x - self.offset_x) / self.zoom_level
        logical_mouse_y = self.logical_center_y + (mouse_y - self.offset_y) / self.zoom_level

        self.zoom_level = new_zoom

        self.offset_x = mouse_x - (logical_mouse_x - self.logical_center_x) * self.zoom_level
        self.offset_y = mouse_y - (logical_mouse_y - self.logical_center_y) * self.zoom_level

    def zoom_in(self, mouse_x, mouse_y):
        self._zoom(self.zoom_step, mouse_x, mouse_y)

    def zoom_out(self, mouse_x, mouse_y):
        self._zoom(1 / self.zoom_step, mouse_x, mouse_y)

    def _scale_point(self, x, y):
        scaled_x = self.offset_x + (x - self.logical_center_x) * self.zoom_level
        scaled_y = self.offset_y + (y - self.logical_center_y) * self.zoom_level
        return scaled_x, scaled_y

    @property
    def scale_func(self):
        func = self._scale_point
        return func

    def _update_canvas_dimensions(self):
        print("Vis _update_canvas_dimensions: Start")
        self.root.update_idletasks()
        new_width = self.canvas.winfo_width()
        new_height = self.canvas.winfo_height()
        print(f"Vis _update_canvas_dimensions: new_width={new_width}, new_height={new_height}")
        if new_width > 1 and new_height > 1 and (new_width != self.canvas_width or new_height != self.canvas_height):
            print(f"Vis _update_canvas_dimensions: Canvas resized to: {new_width}x{new_height}")
            self.canvas_width = new_width
            self.canvas_height = new_height
            self._calculate_map_center(preserve_logical_center=True)
            print("Vis _update_canvas_dimensions: End (resized)")
            return True
        print("Vis _update_canvas_dimensions: End (no resize)")
        return False

    def _on_resize(self, event=None):
        if event and event.widget == self.root:
            if self._update_canvas_dimensions():
                self._calculate_map_center(preserve_logical_center=True)

    def add_object(self, obj):
        self.objects.append(obj)

        if isinstance(obj, RoadObject) and obj.road_id:
            self.road_objects[obj.road_id] = obj

        needs_recalc = False
        if isinstance(obj, RoadObject):
            if obj.x1 < self.min_x: self.min_x = obj.x1; needs_recalc=True
            if obj.x2 < self.min_x: self.min_x = obj.x2; needs_recalc=True
            if obj.x1 > self.max_x: self.max_x = obj.x1; needs_recalc=True
            if obj.x2 > self.max_x: self.max_x = obj.x2; needs_recalc=True
            if obj.y1 < self.min_y: self.min_y = obj.y1; needs_recalc=True
            if obj.y2 < self.min_y: self.min_y = obj.y2; needs_recalc=True
            if obj.y1 > self.max_y: self.max_y = obj.y1; needs_recalc=True
            if obj.y2 > self.max_y: self.max_y = obj.y2; needs_recalc=True
        elif hasattr(obj, 'x') and hasattr(obj, 'y'):
            obj_x = obj.x
            obj_y = obj.y
            width = getattr(obj, 'width', 0)
            height = getattr(obj, 'height', 0)
            if obj_x - width/2 < self.min_x: self.min_x = obj_x - width/2; needs_recalc=True
            if obj_x + width/2 > self.max_x: self.max_x = obj_x + width/2; needs_recalc=True
            if obj_y - height/2 < self.min_y: self.min_y = obj_y - height/2; needs_recalc=True
            if obj_y + height/2 > self.max_y: self.max_y = obj_y + height/2; needs_recalc=True

        if needs_recalc:
            self._calculate_map_center(preserve_logical_center=False)

    async def run(self):
        print("Vis run: Start")
        self.status_label.config(text="Simulation Status: Running")
        self._calculate_map_center(preserve_logical_center=False)

        interp_factor = 0.2

        print("Vis run: Entering main loop")
        frame_count = 0
        while self.running:
            frame_count += 1
            try:
                self.update_road_vehicle_counts()

                self.canvas.delete("all")
                self.draw_background()

                scale = self.scale_func
                zoom = self.zoom_level  # Get current zoom level

                def sort_key(obj):
                    if isinstance(obj, RoadObject): return 0
                    if isinstance(obj, VehicleObject): return 2
                    return 1

                for obj in sorted(self.objects, key=sort_key):
                    if isinstance(obj, RoadObject):
                        obj.render(self.canvas, scale, zoom)
                    elif isinstance(obj, MapObject):
                        if isinstance(obj, VehicleObject) and obj.agent and hasattr(obj.agent, "x") and hasattr(obj.agent, "y"):
                            agent_x = obj.agent.x
                            agent_y = obj.agent.y
                            target_render_x, target_render_y = scale(agent_x, agent_y)

                            if obj.render_x is None or obj.render_y is None:
                                obj.render_x, obj.render_y = target_render_x, target_render_y
                            else:
                                obj.render_x += (target_render_x - obj.render_x) * interp_factor
                                obj.render_y += (target_render_y - obj.render_y) * interp_factor

                            obj.render(self.canvas, obj.render_x, obj.render_y, scale, zoom)

                        elif hasattr(obj, 'x') and hasattr(obj, 'y'):
                            obj.render(self.canvas, scale, zoom)

                self.update_info_panels()
                current_status = self.status_label.cget("text").split(" |")[0]
                self.status_label.config(text=f"{current_status} | Zoom: {self.zoom_level:.2f}x")

                self.root.update()
                await asyncio.sleep(0.03)

            except Exception as e:
                print(f"!!!!!!!! ERROR IN VIS RUN LOOP !!!!!!!!")
                import traceback
                traceback.print_exc()
                self.running = False
                self.status_label.config(text=f"Simulation Status: ERROR - {e}")
                break

        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except tk.TclError:
            pass

    def _calculate_map_center(self, preserve_logical_center=False):
        print(f"Vis _calculate_map_center: Start (preserve={preserve_logical_center})")
        if not preserve_logical_center:
            if not self.objects or self.min_x == float('inf') or self.max_x == float('-inf'):
                self.logical_center_x = 0
                self.logical_center_y = 0
                print("Vis _calculate_map_center: No objects/bounds, center set to (0,0)")
            else:
                self.logical_center_x = (self.min_x + self.max_x) / 2
                self.logical_center_y = (self.min_y + self.max_y) / 2
                print(f"Vis _calculate_map_center: Bounds calculated, center set to ({self.logical_center_x:.1f},{self.logical_center_y:.1f})")

        canvas_center_x = self.canvas_width / 2
        canvas_center_y = self.canvas_height / 2

        self.offset_x = canvas_center_x
        self.offset_y = canvas_center_y
        print(f"Vis _calculate_map_center: End - Offset=({self.offset_x:.1f},{self.offset_y:.1f}), Zoom={self.zoom_level:.2f}")

    def update_road_vehicle_counts(self):
        for road_obj in self.road_objects.values():
            road_obj.current_vehicles = 0
        for obj in self.objects:
            if isinstance(obj, VehicleObject) and obj.agent:
                is_driving = getattr(obj.agent, 'parking_state', 'driving') == 'driving'
                has_roads = hasattr(obj.agent, 'roads') and obj.agent.roads
                current_pos_valid = hasattr(obj.agent, 'current_position') and 0 <= obj.agent.current_position < len(obj.agent.roads)
                if is_driving and has_roads and current_pos_valid:
                    road_tuple = obj.agent.roads[obj.agent.current_position]
                    if isinstance(road_tuple, (list, tuple)) and len(road_tuple) >= 6:
                        road_id = road_tuple[5]
                        if road_id in self.road_objects:
                            self.road_objects[road_id].current_vehicles += 1

    def draw_background(self):
        if self.zoom_level <= 0:
            print("Vis draw_background: WARNING - zoom_level is zero or negative!")
            return

        base_grid_spacing = 50
        grid_spacing = max(0.1, base_grid_spacing * self.zoom_level)

        if abs(self.zoom_level) < 1e-9:
            print("Vis draw_background: Zoom level too small, skipping grid draw.")
            return

        top_left_lx = self.logical_center_x + (0 - self.offset_x) / self.zoom_level
        top_left_ly = self.logical_center_y + (0 - self.offset_y) / self.zoom_level
        start_grid_x = (top_left_lx // base_grid_spacing) * base_grid_spacing
        start_grid_y = (top_left_ly // base_grid_spacing) * base_grid_spacing

        start_screen_x = self.offset_x + (start_grid_x - self.logical_center_x) * self.zoom_level
        start_screen_y = self.offset_y + (start_grid_y - self.logical_center_y) * self.zoom_level

        x = start_screen_x
        while x < self.canvas_width:
            if grid_spacing > 3:
                self.canvas.create_line(int(x), 0, int(x), self.canvas_height, fill="#e8e8e8", dash=(2, 4))
            x += grid_spacing
        x = start_screen_x - grid_spacing
        while x > 0:
            if grid_spacing > 3:
                self.canvas.create_line(int(x), 0, int(x), self.canvas_height, fill="#e8e8e8", dash=(2, 4))
            x -= grid_spacing

        y = start_screen_y
        while y < self.canvas_height:
            if grid_spacing > 3:
                self.canvas.create_line(0, int(y), self.canvas_width, int(y), fill="#e8e8e8", dash=(2, 4))
            y += grid_spacing
        y = start_screen_y - grid_spacing
        while y > 0:
            if grid_spacing > 3:
                self.canvas.create_line(0, int(y), self.canvas_width, int(y), fill="#e8e8e8", dash=(2, 4))
            y -= grid_spacing

    def update_info_panels(self):
        vehicle_lines = []
        parking_lines = []
        light_lines = []
        crossing_lines = []
        road_lines = []

        for obj in self.objects:
            if isinstance(obj, VehicleObject) and obj.agent:
                status_info = ""
                parking_state = getattr(obj.agent, 'parking_state', None)
                if parking_state and parking_state != "driving":
                    status_info = f" [{parking_state.upper()}]"
                    target_parking = getattr(obj.agent, 'target_parking', None)
                    if parking_state == "parked" and target_parking: status_info += f" @ {target_parking}"
                elif hasattr(obj.agent, 'movement_progress'):
                    status_info = f" ({int(obj.agent.movement_progress*100)}%)"

                road_info = ""
                if parking_state == "driving" and hasattr(obj.agent, 'current_position') and hasattr(obj.agent, 'roads') and obj.agent.roads and 0 <= obj.agent.current_position < len(obj.agent.roads):
                    road_tuple = obj.agent.roads[obj.agent.current_position]
                    if isinstance(road_tuple, (list, tuple)) and len(road_tuple) >= 6: road_info = f" on {road_tuple[5]}"

                target_info = ""
                target_parking = getattr(obj.agent, 'target_parking', None)
                if target_parking and parking_state == "driving": target_info = f" -> {target_parking}"

                real_x = int(getattr(obj.agent, "x", 0))
                real_y = int(getattr(obj.agent, "y", 0))
                vehicle_lines.append(f"{obj.id}: ({real_x},{real_y}){status_info}{road_info}{target_info}")

            elif isinstance(obj, ParkingAreaObject) and obj.agent:
                cap_info = "[No Cap]"
                state = ""
                if hasattr(obj.agent, 'current_occupancy') and hasattr(obj.agent, 'capacity'):
                    cap_info = f"({obj.agent.current_occupancy}/{obj.agent.capacity})"
                    if getattr(obj.agent, 'is_full', False): state = " [FULL]"
                parking_lines.append(f"{obj.id} ({obj.parking_type}) {cap_info}{state}")

            elif isinstance(obj, TrafficLightObject) and obj.agent:
                state = getattr(obj.agent, 'state', '[No State]').upper()
                light_lines.append(f"{obj.id}: {state}")

            elif isinstance(obj, PedestrianCrossingObject) and obj.agent:
                status = "OCCUPIED" if getattr(obj.agent, 'is_occupied', False) else "FREE"
                crossing_lines.append(f"{obj.id}: {status}")

            elif isinstance(obj, RoadObject) and obj.road_id:
                color_state = ""
                if obj.current_color == "orange": color_state = "[FULL]"
                elif obj.current_color == "yellow": color_state = "[BUSY]"
                road_lines.append(f"{obj.road_id}: {obj.current_vehicles}/{obj.capacity} {color_state}")

        current_yview_left_text = self.left_info_text.yview()
        self.left_info_text.config(state="normal")
        self.left_info_text.delete('1.0', tk.END)

        vehicle_lines_sorted = sorted(
            vehicle_lines,
             key=lambda line: int(line.split(":")[0].split("_")[1])
        )
        self.left_info_text.insert(tk.END, "\n".join(vehicle_lines_sorted) if vehicle_lines else "(No vehicles)")
        self.left_info_text.yview_moveto(current_yview_left_text[0])
        self.left_info_text.config(state="disabled")

        current_yview_right_text = self.right_info_text.yview()
        self.right_info_text.config(state="normal")
        self.right_info_text.delete('1.0', tk.END)
        content_added = False
        if road_lines:
            self.right_info_text.insert(tk.END, "--- Roads ---\n" + "\n".join(sorted(road_lines)) + "\n\n"); content_added=True
        if parking_lines:
            self.right_info_text.insert(tk.END, "--- Parking ---\n" + "\n".join(sorted(parking_lines)) + "\n\n"); content_added=True
        if light_lines:
            self.right_info_text.insert(tk.END, "--- Traffic Lights ---\n" + "\n".join(sorted(light_lines)) + "\n\n"); content_added=True
        if crossing_lines:
            self.right_info_text.insert(tk.END, "--- Crossings ---\n" + "\n".join(sorted(crossing_lines)) + "\n\n"); content_added=True
        if not content_added:
            self.right_info_text.insert(tk.END, "(No infrastructure data)")
        self.right_info_text.yview_moveto(current_yview_right_text[0])
        self.right_info_text.config(state="disabled")

    def stop(self):
        self.running = False
        self.status_label.config(text="Simulation Status: Stopped by user")

async def main():
    print("Main: Creating Visualizer")
    vis = TrafficSimulationVisualizer(width=1300, height=750)
    print("Main: Visualizer created")

    class DummyAgent: pass
    class DummyVehicleAgent(DummyAgent): x, y, wait_times, parking_state, current_position, roads, movement_progress, target_parking = 50, 50, [0], "driving", 0, [(0,0,200,0, 2, 'R1')], 0.5, "P1"
    class DummyParkingAgent(DummyAgent): current_occupancy, capacity, is_full = 1, 5, False
    class DummyTLAgent(DummyAgent): state = "GREEN"
    class DummyCrossingAgent(DummyAgent): is_occupied = False

    vis.add_object(RoadObject(0, 0, 200, 0, road_id="R1", capacity=3))
    vis.add_object(RoadObject(200, 0, 200, 200, road_id="R2", capacity=2))
    vis.add_object(RoadObject(0, 0, 0, 200, road_id="R3", capacity=2))
    vis.add_object(RoadObject(0, 200, 200, 200, road_id="R4", capacity=4))
    vis.add_object(ParkingAreaObject("P1", DummyParkingAgent(), x=250, y=50, parking_type="street"))
    vis.add_object(ParkingAreaObject("P2", DummyParkingAgent(), x=50, y=250, parking_type="building"))
    vis.add_object(TrafficLightObject("TL1", DummyTLAgent(), x=200, y=-10))
    vis.add_object(PedestrianCrossingObject("PC1", DummyCrossingAgent(), x=100, y=200))

    veh1_agent = DummyVehicleAgent()
    vis.add_object(VehicleObject("V1", veh1_agent))
    veh2_agent = DummyVehicleAgent(); veh2_agent.x, veh2_agent.y = 10, 150; veh2_agent.roads = [(0,0,0,200, 2, 'R3')]; veh2_agent.parking_state = "driving"; veh2_agent.target_parking = "P2"; vis.add_object(VehicleObject("V2", veh2_agent))
    veh3_agent = DummyVehicleAgent(); veh3_agent.x, veh3_agent.y = 250, 50; veh3_agent.parking_state = "parked"; veh3_agent.target_parking = "P1"; vis.add_object(VehicleObject("V3", veh3_agent))

    print("Main: Dummy objects added")

    async def update_dummies():
        import random
        count = 0
        p1_agent = vis.objects[4].agent
        tl1_agent = vis.objects[6].agent
        pc1_agent = vis.objects[7].agent

        while vis.running:
            await asyncio.sleep(1)
            count += 1
            if veh1_agent.parking_state == "driving":
                current_road_id = veh1_agent.roads[veh1_agent.current_position][5]
                if current_road_id == 'R1':
                    veh1_agent.x = min(200, veh1_agent.x + 15)
                    veh1_agent.movement_progress = veh1_agent.x / 200
                    if veh1_agent.x >= 200:
                        veh1_agent.current_position = 1
                        veh1_agent.roads = [(0,0,200,0, 2, 'R1'), (200,0,200,200, 2, 'R2')]
                        veh1_agent.x, veh1_agent.y = 200, 0
                        veh1_agent.movement_progress = 0
                elif current_road_id == 'R2':
                    veh1_agent.y = min(200, veh1_agent.y + 15)
                    veh1_agent.movement_progress = veh1_agent.y / 200

            if count % 5 == 0: tl1_agent.state = random.choice(["GREEN", "RED"])
            if count % 7 == 0: pc1_agent.is_occupied = not pc1_agent.is_occupied
            if count % 10 == 0 and p1_agent.current_occupancy < p1_agent.capacity:
                p1_agent.current_occupancy += 1
                p1_agent.is_full = (p1_agent.current_occupancy >= p1_agent.capacity)

    try:
        print("Main: Starting UI updates and initial calculations")
        vis.root.update()
        vis.root.update_idletasks()
        print("Main: Calling _update_canvas_dimensions")
        vis._update_canvas_dimensions()
        print("Main: Calling _calculate_map_center")
        vis._calculate_map_center(preserve_logical_center=False)
        print("Main: Initial setup complete, starting asyncio.gather")

        await asyncio.gather(
            vis.run(),
            update_dummies()
        )
    except tk.TclError as e:
        if "application has been destroyed" not in str(e):
            print(f"Tkinter error: {e}")
        else: print("Tkinter window closed.")
    except asyncio.CancelledError:
        print("Simulation tasks cancelled.")
    except Exception as e:
        print(f"!!!!!!!! ERROR IN MAIN SETUP/GATHER !!!!!!!!")
        import traceback
        traceback.print_exc()
    finally:
        print("Main: Finally block reached")
        vis.stop()

if __name__ == "__main__":
    try:
        print("Script: Starting asyncio.run(main())")
        asyncio.run(main())
        print("Script: asyncio.run(main()) finished")
    except KeyboardInterrupt:
        print("Simulation interrupted by user.")
    except Exception as e:
        print(f"!!!!!!!! TOP LEVEL SCRIPT ERROR !!!!!!!!")
        import traceback
        traceback.print_exc()
