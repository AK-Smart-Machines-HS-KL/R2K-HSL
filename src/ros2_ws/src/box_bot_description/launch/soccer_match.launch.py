import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

def generate_launch_description():
    pkg_name = 'box_bot_description'
    urdf_file = 'box_bot_v3.urdf'
    world_file = 'robocup.world'

    try:
        pkg_share = get_package_share_directory(pkg_name)
        urdf_path = os.path.join(pkg_share, 'urdf', urdf_file)
        world_path = os.path.join(pkg_share, 'worlds', world_file)
    except:
        urdf_path = os.path.join(os.getcwd(), 'src/box_bot_description/urdf', urdf_file)
        world_path = os.path.join(os.getcwd(), 'src/box_bot_description/worlds', world_file)

    # 1. Start Gazebo (MIT ROS INIT, WICHTIG!)
    gazebo = ExecuteProcess(
        cmd=['gazebo', '--verbose', world_path, 
             '-s', 'libgazebo_ros_init.so', 
             '-s', 'libgazebo_ros_factory.so'],
        output='screen'
    )

    # 2. Spawn Goalie
    spawn_r2k_1 = Node(
        package='gazebo_ros', executable='spawn_entity.py',
        arguments=['-entity', 'R2K_1', '-file', urdf_path, '-robot_namespace', 'robot1', 
                   '-x', '-4.5', '-y', '0', '-z', '0.01', '-Y', '0'],
        output='screen'
    )

    # 3. Spawn Defender 1
    spawn_r2k_2 = Node(
        package='gazebo_ros', executable='spawn_entity.py',
        arguments=['-entity', 'R2K_2', '-file', urdf_path, '-robot_namespace', 'robot2', 
                   '-x', '-2.5', '-y', '1.0', '-z', '0.01', '-Y', '0'],
        output='screen'
    )

    # 4. Spawn Defender 2
    spawn_r2k_3 = Node(
        package='gazebo_ros', executable='spawn_entity.py',
        arguments=['-entity', 'R2K_3', '-file', urdf_path, '-robot_namespace', 'robot3', 
                   '-x', '-2.5', '-y', '-1.0', '-z', '0.01', '-Y', '0'],
        output='screen'
    )

    return LaunchDescription([gazebo, spawn_r2k_1, spawn_r2k_2, spawn_r2k_3])
