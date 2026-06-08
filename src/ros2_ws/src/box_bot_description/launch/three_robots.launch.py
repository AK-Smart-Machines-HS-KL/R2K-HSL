import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

def generate_launch_description():
    pkg_name = 'box_bot_description'
    urdf_file = 'box_bot_v3.urdf'

    try:
        pkg_share = get_package_share_directory(pkg_name)
        urdf_path = os.path.join(pkg_share, 'urdf', urdf_file)
    except:
        urdf_path = os.path.join(os.getcwd(), 'src/box_bot_description/urdf', urdf_file)

    gazebo = ExecuteProcess(
        cmd=['gazebo', '--verbose', '-s', 'libgazebo_ros_factory.so'],
        output='screen'
    )

    # Spawn Z = 0.01 (1cm) to let wheels settle on ground
    # Chassis is already lifted by URDF offsets
    
    spawn_robot1 = Node(
        package='gazebo_ros', executable='spawn_entity.py',
        arguments=['-entity', 'robot1', '-file', urdf_path, '-robot_namespace', 'robot1', 
                   '-x', '0', '-y', '0', '-z', '0.01'],
        output='screen'
    )

    spawn_robot2 = Node(
        package='gazebo_ros', executable='spawn_entity.py',
        arguments=['-entity', 'robot2', '-file', urdf_path, '-robot_namespace', 'robot2', 
                   '-x', '2', '-y', '0', '-z', '0.01'],
        output='screen'
    )

    spawn_robot3 = Node(
        package='gazebo_ros', executable='spawn_entity.py',
        arguments=['-entity', 'robot3', '-file', urdf_path, '-robot_namespace', 'robot3', 
                   '-x', '-2', '-y', '0', '-z', '0.01'],
        output='screen'
    )

    return LaunchDescription([gazebo, spawn_robot1, spawn_robot2, spawn_robot3])
