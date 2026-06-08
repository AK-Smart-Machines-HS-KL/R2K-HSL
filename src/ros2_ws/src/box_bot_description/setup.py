from setuptools import setup
import os
from glob import glob

package_name = 'box_bot_description'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'launch', 'back'), glob('launch/back/*.launch.py')),
        (os.path.join('share', package_name, 'robot'), glob('robot/*')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.world')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@todo.todo',
    description='Ros2K BoxBot Project',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'circle_drive = box_bot_description.circle_drive:main',
            'worldmodel = box_bot_description.worldmodel:main',
            'navigator = box_bot_description.navigator:main',
            'soccer_dashboard = box_bot_description.soccer_dashboard:main',
            'verify_sensors = box_bot_description.verify_sensors:main',
        ],
    },
)
