from launch import LaunchDescription
from launch.actions import ExecuteProcess, DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    pkg_box_bot = get_package_share_directory('box_bot_description')
    world_path = os.path.join(pkg_box_bot, 'worlds', 'robocup.world')

    headless = LaunchConfiguration('headless')

    return LaunchDescription([
        DeclareLaunchArgument('headless', default_value='false',
                              description='Launch gzserver only (no gzclient GUI)'),
        ExecuteProcess(
            cmd=['gzserver', '--verbose', '-s', 'libgazebo_ros_factory.so', world_path],
            condition=IfCondition(headless),
            output='screen'
        ),
        ExecuteProcess(
            cmd=['gazebo', '--verbose', '-s', 'libgazebo_ros_factory.so', world_path],
            condition=UnlessCondition(headless),
            output='screen'
        ),
        Node(
            package='r2k_scenario_spawner',
            executable='scenario_loader',
            name='scenario_loader',
            output='screen'
        )
    ])
