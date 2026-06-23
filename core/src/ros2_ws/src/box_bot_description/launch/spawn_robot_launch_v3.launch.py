from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('z', default_value='0.0'),
        DeclareLaunchArgument('robot_name', default_value='box_bot'),
        DeclareLaunchArgument('robot_urdf', default_value=''),
        
        Node(
            package='gazebo_ros', executable='spawn_entity.py',
            arguments=[
                '-entity', LaunchConfiguration('robot_name'),
                '-file', LaunchConfiguration('robot_urdf'),
                '-x', LaunchConfiguration('x'),
                '-y', LaunchConfiguration('y'),
                '-z', LaunchConfiguration('z'),
                '-robot_namespace', LaunchConfiguration('robot_name')
            ],
            output='screen'
        )
    ])
