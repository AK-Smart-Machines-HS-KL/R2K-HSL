#!/usr/bin/env python3
import json, os, sys, rclpy, time
from rclpy.node import Node
from gazebo_msgs.srv import SpawnEntity

class Spawner(Node):
    def __init__(self):
        super().__init__('r2k_spawner')
        self.cli = self.create_client(SpawnEntity, '/spawn_entity')
        while not self.cli.wait_for_service(timeout_sec=2.0):
            self.get_logger().info('⏳ Waiting for /spawn_entity service...')

    def spawn(self, name, x, y, urdf):
        self.get_logger().info(f"✨ Spawning {name} at ({x}, {y})")
        with open(urdf, 'r') as f: xml = f.read()
        req = SpawnEntity.Request()
        req.name, req.xml, req.robot_namespace = name, xml, name
        req.initial_pose.position.x, req.initial_pose.position.y, req.initial_pose.position.z = float(x), float(y), 0.2
        return self.cli.call_async(req)

def main():
    print("🚀 [SPAWNER] Booting up...")
    ents = {}
    base_dir = os.getenv('ROS2K_WS', os.getcwd())
    scenario_path = os.path.join(base_dir, "ai_tactics", "active_scenario.json")
    
    try:
        with open(scenario_path, 'r') as f: 
            data = json.load(f)
            ents = data.get("entities", {})
    except Exception as e:
        print(f"⚠️ [SPAWNER] Could not read JSON: {e}")

    if not ents:
        print("⚡ [SPAWNER] Worldstate is empty! Injecting default kickoff positions...")
        ents = {
            "soccer_ball": {"x": 0.0, "y": 0.0},
            "blue_1": {"x": -2.0, "y": 0.0},
            "blue_2": {"x": -3.0, "y": 1.5},
            "red_1": {"x": 2.0, "y": 0.0}
        }

    rclpy.init()
    n = Spawner()
    futures = []
    
    ball_urdf = os.path.join(base_dir, "ros2_ws/src/r2k_scenario_spawner/urdf/football.urdf")
    blue_urdf = os.path.join(base_dir, "ros2_ws/src/r2k_description/urdf/blue_bot.urdf")
    red_urdf = os.path.join(base_dir, "ros2_ws/src/r2k_description/urdf/red_bot.urdf")

    for name, pos in ents.items():
        if name == "soccer_ball": path = ball_urdf
        elif name.startswith("blue"): path = blue_urdf
        elif name.startswith("red"): path = red_urdf
        else: continue

        futures.append(n.spawn(name, pos.get("x", 0.0), pos.get("y", 0.0), path))
        time.sleep(1.0)
        
    print("⏳ [SPAWNER] Waiting for entities to drop...")
    time.sleep(2.0)
    print("✅ [SPAWNER] Done!")
    
    n.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
