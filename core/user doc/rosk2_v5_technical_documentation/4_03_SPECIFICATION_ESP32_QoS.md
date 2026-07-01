---
id: 4_03
title: "ESP32 Quality of Service (QoS)"
type: SPECIFICATION
tags: [qos, best_effort, reliable, telemetry, fastdds]
last_modified: 2026-05-31
version: v5_release
---
# ESP32 Quality of Service (QoS)

> [!info] Human Summary
> Details the critical Quality of Service profiles and DDS warm-up routines required to prevent physical network saturation while ensuring hardware components communicate safely.

> [!abstract] LLM Context Anchor
> Sensor telemetry such as `/bot1/battery` MUST be polled using `BEST_EFFORT` QoS reliability. This forces the FastDDS stack to establish a route without queuing stale packets and crashing the micro-ROS agent memory buffer.
> **[NEW in v5]:** The QoS stabilization protocol is now dynamically handled via `launch_r2k.sh`. Depending on the active Hybrid OS configuration, the `BEST_EFFORT` probe executes either natively against the `uros_ws` agent (Ubuntu 22.04) or via isolated `docker exec` commands (Ubuntu 24.04).

## 1. System Topology of Asymmetrical QoS and Warm-Up

**[DEPRECATED in v4] Original Topology:**
This graph illustrates the network forcing technique used to stabilize physical DDS routes before injecting high-frequency motor commands.

~~~mermaid
graph TD
    subgraph Bridge ["Python Execution"]
        Pub["cmd_vel Publisher"]
    end

    subgraph Network ["Wi-Fi FastDDS"]
        WarmUp["BEST_EFFORT Probe"]
        REL["RELIABLE Queue"]
    end

    subgraph Hardware ["Yahboom ESP32"]
        Batt["Battery Topic"]
        Motors["Motor Driver"]
    end

    Batt -->|1. Probe Topic| WarmUp
    WarmUp -->|2. Establishes Route| Bridge
    Pub -->|3. Critical Command| REL
    REL -->|TCP-like Guarantee| Motors

    style WarmUp fill:#fff3cd,stroke:#856404
    style REL fill:#dfd,stroke:#333
~~~

**[NEW in v5] Hybrid OS QoS Topology:**
The underlying DDS protocol remains identical, but the warm-up injection path dynamically adapts to the host operating system constraints.

~~~mermaid
graph TD
    subgraph Bridge ["ollama_sandbox_bridge.py"]
        Pub["cmd_vel Publisher"]
    end

    subgraph Injector ["launch_r2k.sh (DDS Warm-Up)"]
        U22["Native ros2 topic echo"]
        U24["Docker ros2 topic echo"]
    end

    subgraph Network ["Wi-Fi FastDDS"]
        WarmUp["BEST_EFFORT Probe"]
        REL["RELIABLE Queue"]
    end

    subgraph Hardware ["Yahboom ESP32"]
        Batt["/bot1/battery Topic"]
        Motors["Motor Driver"]
    end

    U22 --> WarmUp
    U24 --> WarmUp
    Batt -->|1. Await Topic| Injector
    WarmUp -->|2. Establishes Route| Bridge
    Pub -->|3. Critical Command| REL
    REL -->|TCP-like Guarantee| Motors

    style Injector fill:#fcc,stroke:#c00
    style WarmUp fill:#fff3cd,stroke:#856404
    style REL fill:#dfd,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] Legacy Flow:**
When a physical micro-ROS agent boots, the DDS network requires time to stabilize topic routing tables. If the system immediately blasts `RELIABLE` motor commands before the route is fully validated, packets queue indefinitely, eventually causing a buffer overflow on the ESP32.

To mitigate this, ROS2K launch scripts perform a "DDS Warm-Up". The script polls a benign hardware topic (like `/bot1/battery`) explicitly using `BEST_EFFORT` QoS. This forces the network stack to validate the path to the physical agent safely. If a packet drops during this probe, the system ignores it. Once the battery topic returns successfully, the system knows the route is stable and it is safe to begin transmitting `RELIABLE` `/cmd_vel` instructions.

**[UPDATE in v5] Hybrid Environment Warm-Up:**
This principle is fully preserved in V5. However, due to the OS divergence, `launch_r2k.sh` now sets a strict 10-second timeout block for hardware discovery. Once `/bot1/battery` is registered on the Domain 0 bus, the script executes a silent background `ros2 topic echo --once --qos-reliability best_effort` using either the host's native `ros2` CLI or the containerized workspace, finalizing the FastDDS tree before `ollama_sandbox_bridge.py` is permitted to boot.

## 3. Code Reference & Interfaces
> **Source:** `triple_demo_launch.sh` **[DEPRECATED in v4]**
> **Source:** `launch_r2k.sh` **[NEW in v5]**

**[DEPRECATED in v4] Legacy Warm-Up:**
The shell script logic utilizing `ros2 topic echo` to execute a `BEST_EFFORT` network probe on the physical hardware.
~~~bash
# snippet from triple_demo_launch.sh
echo "Warte auf echtes Yahboom Signal /bot1/battery..."

until docker exec r2k_unify2_gazebo bash -c "source /opt/ros/humble/setup.bash && ros2 topic list 2>/dev/null" | grep -q "/bot1/battery"; do
    sleep 1
done

echo "🔋 Batterie-Topic erkannt! Führe DDS Warm-Up durch..."
# Der BEST_EFFORT Lesezugriff zwingt das Netzwerk, die Route zum ESP32 aufzubauen
docker exec -i r2k_unify2_gazebo bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo --once --qos-reliability best_effort /bot1/battery"
~~~

**[NEW in v5] Hybrid OS Warm-Up:**
The updated logic evaluates the `UBUNTU_VERSION` to determine the execution namespace, and implements a non-blocking 10-second timeout to prevent indefinite hangups.
~~~bash
# snippet from launch_r2k.sh
if [ "$YAHBOOM_READY" = false ] && ros2 topic list 2>/dev/null | grep -q "/bot1/battery"; then
    echo "🔋 Yahboom Topic erkannt! Führe DDS Warm-Up durch..."
    
    if [ "$UBUNTU_VERSION" == "22.04" ]; then
        ros2 topic echo --once --qos-reliability best_effort /bot1/battery > /dev/null 2>&1 &
    else
        docker exec -i $CONTAINER_NAME bash -c "$SOURCE_CMD && ros2 topic echo --once --qos-reliability best_effort /bot1/battery > /dev/null 2>&1" &
    fi
    
    echo "✅ YAHBOOM BEREIT!"
    YAHBOOM_READY=true
fi
~~~

## 4. Known Issues & Limitations
* If the hardware fails to publish the battery topic due to a firmware error, the launch script will hang indefinitely in the `until` loop. **[UPDATE in v5: Mitigated by a 10-second bounded while-loop, though the AI bridge may crash later if hardware remains offline.]**
* If publisher and subscriber QoS configurations do not match perfectly, ROS 2 topics fail silently without throwing terminal errors.
* **[NEW in v5]:** If the host firewall drops UDP Multicast discovery packets on Ubuntu 24.04, the loop polling `/bot1/battery` will silently timeout, forcing the system to launch blindly and resulting in dropped `Twist` messages.

## 5. Glossary
* **QoS (Quality of Service):** Policies in ROS 2 dictating data handling rules over the network.
* **BEST_EFFORT:** UDP-style policy; attempts delivery but drops lost packets.
* **RELIABLE:** TCP-style policy; guarantees delivery by retrying.
* **DDS Warm-Up:** The act of explicitly pinging a low-risk topic to force network route generation.
