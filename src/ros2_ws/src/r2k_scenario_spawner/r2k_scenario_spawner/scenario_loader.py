import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SpawnEntity
import json
import os
import math

def euler_to_quaternion(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)

class ScenarioLoader(Node):
    def __init__(self):
        super().__init__('scenario_loader')
        self.client = self.create_client(SpawnEntity, '/spawn_entity')
        while not self.client.wait_for_service(timeout_sec=2.0):
            self.get_logger().info('Waiting for Gazebo /spawn_entity service...')
        self.spawn_from_json()

    def spawn_entity(self, name, xml_path, x, y, yaw, namespace):
        request = SpawnEntity.Request()
        request.name = name
        try:
            with open(xml_path, 'r') as f:
                request.xml = f.read()
        except FileNotFoundError:
            self.get_logger().error(f"URDF missing: {xml_path}")
            return

        request.robot_namespace = namespace
        request.initial_pose.position.x = float(x)
        request.initial_pose.position.y = float(y)
        request.initial_pose.position.z = 0.1 
        qx, qy, qz, qw = euler_to_quaternion(float(yaw))
        request.initial_pose.orientation.x = qx
        request.initial_pose.orientation.y = qy
        request.initial_pose.orientation.z = qz
        request.initial_pose.orientation.w = qw

        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        if future.result().success:
            self.get_logger().info(f"Successfully spawned: {name} at ({x}, {y})")
        else:
            self.get_logger().error(f"Failed to spawn: {name}")

    def spawn_from_json(self):
        base_dir = os.getenv('ROS2K_WS', os.getcwd())
        json_path = os.path.join(base_dir, 'shared_state', 'scene.json')
        bot_urdf = os.path.join(base_dir, 'ros2_ws/src/box_bot_description/urdf/box_bot_v3.urdf')
        ball_urdf = os.path.join(base_dir, 'ros2_ws/src/r2k_scenario_spawner/urdf/football.urdf')

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            return

        ball_pos = data['ball']['t_now']
        self.spawn_entity('soccer_ball', ball_urdf, ball_pos['x']*0.1, ball_pos['y']*0.1, ball_pos.get('theta_rad', 0), '/ball')

        for bot_id, bot_data in data.get('blue_team', {}).items():
            pos = bot_data['t_now']
            self.spawn_entity(bot_id, bot_urdf, pos['x']*0.1, pos['y']*0.1, pos['theta_rad'], f'/{bot_id}')

        for bot_id, bot_data in data.get('red_team', {}).items():
            pos = bot_data['t_now']
            self.spawn_entity(bot_id, bot_urdf, pos['x']*0.1, pos['y']*0.1, pos['theta_rad'], f'/{bot_id}')

def main():
    rclpy.init()
    node = ScenarioLoader()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
