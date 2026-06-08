import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import TextSubstitution

def generate_launch_description():
    pkg = get_package_share_directory('box_bot_description')
    urdf = os.path.join(pkg, 'robot', 'box_bot_v2.urdf')
    world = os.path.join(pkg, 'worlds', 'box_bot_empty.world')

    # Start Gazebo
    gazebo = ExecuteProcess(
        cmd=['gazebo', '--verbose', world, '-s', 'libgazebo_ros_init.so', '-s', 'libgazebo_ros_factory.so'],
        output='screen'
    )

    # Spawn 3 Robots
    spawn_cmds = []
    for i in range(3):
        spawn_cmds.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'spawn_robot_launch_v3.launch.py')),
                launch_arguments={
                    'robot_urdf': urdf,
                    'x': str(float(i)), 'y': '0.0', 'z': '0.05',
                    'robot_name': f'box_bot{i}'
                }.items()
            )
        )

    ld = LaunchDescription()
    ld.add_action(gazebo)
    for cmd in spawn_cmds:
        ld.add_action(cmd)
    return ld
