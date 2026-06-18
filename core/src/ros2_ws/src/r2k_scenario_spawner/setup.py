from setuptools import setup
import os
from glob import glob

package_name = 'r2k_scenario_spawner'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.urdf')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    description='Master Scenario Spawner',
    license='TODO',
    entry_points={
        'console_scripts': [
            'scenario_loader = r2k_scenario_spawner.scenario_loader:main',
        ],
    },
)
