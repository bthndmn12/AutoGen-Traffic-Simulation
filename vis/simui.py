import tkinter as tk
import asyncio

class MapObject:
    def __init__(self, id, x, y):
        self.id = id
        self.x = x
        self.y = y

    def render(self, canvas):
        raise NotImplementedError("Subclasses should implement render method")


class VehicleObject(MapObject):
    def __init__(self, id, agent, x=50, y=290):
        super().__init__(id, x, y)
        self.agent = agent
        self.color_cycle = ["blue", "cyan", "navy", "purple"]

    def render(self, canvas):
        print(f"Rendering Vehicle: {self.id} at y={self.y}")
        if self.agent:
            position = self.x + (self.agent.current_position * 40)  # exaggerate movement for visibility
            position = max(self.x, min(position, self.x + 600))
            color = self.color_cycle[self.agent.current_position % len(self.color_cycle)]
            canvas.create_rectangle(position - 10, self.y, position + 10, self.y + 20, fill=color, outline='black')
            canvas.create_text(position, self.y - 10, text=f"{self.id} ({position})")
        else:
            canvas.create_rectangle(self.x - 10, self.y, self.x + 10, self.y + 20, fill='gray', outline='black')
            canvas.create_text(self.x, self.y - 10, text=f"{self.id} (no agent)")


class TrafficLightObject(MapObject):
    def __init__(self, id, agent, x=300, y=250):
        super().__init__(id, x, y)
        self.agent = agent

    def render(self, canvas):
        print(f"Rendering Traffic Light: {self.id} at y={self.y}")
        if self.agent:
            light_color = "green" if self.agent.state.upper() == "GREEN" else "red"
            canvas.create_oval(self.x, self.y, self.x + 20, self.y + 20, fill=light_color, outline='black')
            canvas.create_text(self.x + 10, self.y - 10, text=f"{self.id}")
        else:
            canvas.create_oval(self.x, self.y, self.x + 20, self.y + 20, fill="gray", outline='black')
            canvas.create_text(self.x + 10, self.y - 10, text=f"{self.id} (no agent)")


class PedestrianCrossingObject(MapObject):
    def __init__(self, id, agent, x=320, y=270):
        super().__init__(id, x, y)
        self.agent = agent

    def render(self, canvas):
        print(f"Rendering Crossing: {self.id} at y={self.y}")
        if self.agent:
            color = "orange" if self.agent.is_occupied else "white"
            canvas.create_rectangle(self.x, self.y, self.x + 40, self.y + 50, fill=color, outline='black')
            canvas.create_text(self.x + 20, self.y - 10, text=f"{self.id}")
        else:
            canvas.create_rectangle(self.x, self.y, self.x + 40, self.y + 50, fill="gray", outline='black')
            canvas.create_text(self.x + 20, self.y - 10, text=f"{self.id} (no agent)")


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

    def add_object(self, obj):
        print(f"Added object: {obj.id}")
        self.objects.append(obj)

    async def run(self):
        while self.running:
            self.canvas.delete("all")
            self.draw_background()
            for obj in self.objects:
                obj.render(self.canvas)

            self.update_info_label()
            self.root.update()
            await asyncio.sleep(0.1)
        self.root.destroy()

    def draw_background(self):
        # Draw a simple road for reference
        road_top = self.height // 2 - 30
        road_bottom = self.height // 2 + 30
        self.canvas.create_rectangle(0, road_top, self.width, road_bottom, fill="gray")
        self.canvas.create_text(10, road_top - 10, anchor="nw", text="[Road Start]")

    def update_info_label(self):
        info_texts = []
        for obj in self.objects:
            if isinstance(obj, VehicleObject) and obj.agent:
                info_texts.append(f"Vehicle {obj.id} Pos: {obj.agent.current_position}")
            elif isinstance(obj, TrafficLightObject) and obj.agent:
                info_texts.append(f"Traffic Light {obj.id}: {obj.agent.state}")
            elif isinstance(obj, PedestrianCrossingObject) and obj.agent:
                status = "occupied" if obj.agent.is_occupied else "free"
                info_texts.append(f"Crossing {obj.id}: {status}")

        self.info_label.config(text=" | ".join(info_texts))

    def stop(self):
        self.running = False
