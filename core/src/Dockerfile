FROM osrf/ros:humble-desktop
ENV DEBIAN_FRONTEND=noninteractive

# 1. Systempakete für Gazebo und ROS
RUN apt-get update && apt-get install -y \
    gazebo ros-humble-gazebo-ros-pkgs python3-pip \
    libxcb-cursor0 libgl1-mesa-glx libxkbcommon-x11-0 libegl1 python3-tk \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip

# 2. DER ABSOLUTE FIX: Wir zwingen pip zur strikten Installation von NumPy < 2
# --force-reinstall garantiert, dass keine gecachten, kaputten Versionen verwendet werden!
# NOTE: If colcon fails with "numpy/ndarrayobject.h: No such file or directory", the
# cause is stale cached artifacts in ros2_ws/build/ — NOT a missing numpy installation.
# Fix: rm -rf ros2_ws/build ros2_ws/install, then re-run colcon build. The rosidl CMake
# fallback (python3 -c "import numpy; print(numpy.get_include())") resolves the path
# automatically on a clean build. See AGENTS.md "Docker colcon rebuild (U24)".
RUN pip3 install "numpy<2.0.0" "scipy==1.10.1" "matplotlib==3.7.1" PyQt6 requests "mplsoccer==1.1.12" --force-reinstall

# 3. Code kopieren und ROS sourcen
COPY . /workspace
WORKDIR /workspace
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
