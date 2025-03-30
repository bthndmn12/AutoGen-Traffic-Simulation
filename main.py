import asyncio
from autogen_core import AgentId
from messages.types import MyMessageType
from runtime import setup_runtime
from vis.simui import (
    TrafficSimulationVisualizer,
    VehicleObject,
    TrafficLightObject,
    PedestrianCrossingObject,
)


async def main():
    # set up runtime and agents
    runtime, _, _, _ = await setup_runtime()
    runtime.start()
    await asyncio.sleep(1)  # Let agents initialize

    vehicle = await runtime._get_agent(AgentId("vehicle_1", "default"))
    traffic_light = await runtime._get_agent(AgentId("traffic_light_1", "default"))
    pedestrian = await runtime._get_agent(AgentId("pedestrian_crossing_1", "default"))

    # set up vis
    visualizer = TrafficSimulationVisualizer()
    visualizer.add_object(VehicleObject("vehicle_1", vehicle, x=50, y=300))
    visualizer.add_object(TrafficLightObject("traffic_light_1", traffic_light, x=300, y=250))
    visualizer.add_object(PedestrianCrossingObject("crossing_1", pedestrian, x=320, y=280))

    visualizer_task = asyncio.create_task(visualizer.run())

    # run sim
    for _ in range(20):
        await runtime.send_message(
            MyMessageType(content="move", source="user"),
            AgentId("vehicle_1", "default")
        )
        await asyncio.sleep(1)

    # Shutdown
    await runtime.stop()
    visualizer.stop()
    await visualizer_task


if __name__ == '__main__':
    asyncio.run(main())