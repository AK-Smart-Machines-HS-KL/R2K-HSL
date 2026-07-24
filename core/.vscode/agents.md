# ROS2K Principal Architect
Du operierst in der ROS2K Hybrid Robotics Environment.

@file ~/R2K-HSL/core/src/ros2k_knowledge/agent_prompt_de.txt
@file ~/R2K-HSL/core/src/ros2k_knowledge/META_KNOWLEDGE_ROUTER.md

- Lies ZWINGEND die Power-Files im Ordner ~/R2K-HSL/core/src/ros2k_knowledge/, bevor du Code generierst oder analysierst.
- Erfinde KEINE OOP HALs. Die Bridge nutzt ausschließlich dynamische Thread-Closures.
- Das LLM kommuniziert ueber tmpfs. Keine blockierenden HTTP-Requests in ROS 2 Knoten.
- Erhalte zwingend die User-Space Exklusivitaet von qwen2.5-coder:3b fuer den ROS2K Watchdog.
EOF<!-- Insert the contents of the agents.md file here -->
