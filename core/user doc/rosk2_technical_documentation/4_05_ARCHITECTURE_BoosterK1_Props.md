---
id: 4_05
title: "Booster K1 Biped Architecture"
type: ARCHITECTURE
tags: [booster-k1, biped, rpc, state-machine, api-codes]
last_modified: 2026-05-31
version: v5_release
---
# Booster K1 Biped Architecture

> [!info] Human Summary
> Overviews the integration of the Booster K1 bipedal robot into the ROS2K stack, bypassing standard `cmd_vel` physics in favor of a Remote Procedure Call (RPC) architecture mapped to specific LocoAPI topics.

> [!abstract] LLM Context Anchor
> The Booster K1 hardware interface exposes proprietary SDK endpoints over ROS 2 via `/LocoApiTopicReq` and `/LocoApiTopicResp`. The Bridge node must manage gait transitions explicitly using these topics instead of standard Twist arrays.
> **[NEW in v5]:** The execution logic is now strictly governed by the `active_relay.json` profile. The `ollama_sandbox_bridge.py` directly serializes JSON RPC strings utilizing exact K1 API Codes: `2000` (Failsafe/Prep/Stand) and `2001` (Active Locomotion/Trot). The namespace is explicitly `/bot1/LocoApiTopicReq`.

## 1. System Topology of Bipedal RPC Transitions

**[DEPRECATED in v4] Original Bipedal Topology:**
This graph breaks down the required state machine transitions necessary to move the complex bipedal hardware safely.

~~~mermaid
graph TD
    subgraph Bridge ["Execution Thread"]
        Parse["Parse Target"]
    end

    subgraph K1_State ["Biped State Machine"]
        Idle["Stand Idle"]
        Trot["Trot Gait"]
        Halt["Dynamic Halt"]
    end

    subgraph RPC_Topics ["ROS 2 LocoAPI"]
        Req["LocoApiTopicReq"]
        Resp["LocoApiTopicResp"]
    end

    Parse -->|1. Trigger Stand| Idle
    Idle -->|2. Request Gait| Trot
    Trot -->|3. Publish JSON| Req
    Req -->|Hardware Acts| Resp
    Trot -->|4. Trigger Stop| Halt
    Halt --> Idle

    style Req fill:#bbf,stroke:#333
    style Resp fill:#bbf,stroke:#333
    style Idle fill:#f9f,stroke:#333
~~~

**[NEW in v5] Validated V5 K1 RPC Topology:**
The topology now reflects the specific API Code integers passed directly from the unified Python Bridge, eliminating any OOP HAL abstraction.

~~~mermaid
graph TD
    subgraph Bridge ["ollama_sandbox_bridge.py"]
        Parse["Evaluate active_relay.json"]
        JSON["Serialize JSON Payload"]
    end

    subgraph K1_State ["Biped API Codes"]
        Idle["API 2000 (Prep/Stand)"]
        Trot["API 2001 (Locomotion)"]
    end

    subgraph RPC_Topics ["ROS 2 LocoAPI (/bot1/)"]
        Req["LocoApiTopicReq"]
        Resp["LocoApiTopicResp"]
    end

    Parse -->|1. Transmit Code 2000| Idle
    Idle -->|2. Transmit Code 2001| Trot
    JSON -->|Raw Publish| Req
    Idle -.-> JSON
    Trot -.-> JSON
    Req -->|Hardware SDK| Resp

    style Req fill:#bbf,stroke:#333
    style Resp fill:#bbf,stroke:#333
    style Idle fill:#f9f,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] Legacy Flow:**
Unlike simple wheeled differential robots, a bipedal robot will fall over if sent an immediate high-velocity command. The Booster K1 SDK operates on a strict state machine.

To integrate the K1 with the LLM's pure spatial output, the execution node wraps the spatial targets in an RPC driver. When the LLM commands a move, the Bridge first sends an RPC payload to switch the K1 from `Stand` to `Trot` via `/LocoApiTopicReq`. The launch script enforces a DDS warm-up on `/LocoApiTopicResp` to ensure the route to the biped is stable before issuing these complex gait transitions. Upon reaching the target, it triggers a halt state to balance the biped.

**[UPDATE in v5] V5 API Injection:**
The K1 integration is now seamlessly flattened into `ollama_sandbox_bridge.py`. When a target coordinate is extracted for a robot mapped to a K1 profile in `active_relay.json`, the Bridge calculates the required movement vector (Yaw and Distance). It then constructs a strict stringified JSON payload injecting API Code `2000` to prepare the biped's stance. Following a brief sleep, it publishes API Code `2001` with the embedded translation vectors directly to `/bot1/LocoApiTopicReq`. To trigger the Kinematic Freeze at teardown, the system simply broadcasts Code `2000` again.

## 3. Code Reference & Interfaces
> **Source:** `triple_demo_launch.sh` **[DEPRECATED in v4]**
> **Source:** `launch_r2k.sh` **[NEW in v5]**

**[DEPRECATED in v4] Legacy Warm-Up:**
The warm-up sequence confirming the physical K1 interface is responsive before the Bridge begins transmitting JSON payloads.
~~~bash
# snippet from triple_demo_launch.sh
echo "Warte auf K1-Hardware-Interface /LocoApiTopicReq..."
until docker exec r2k_unify2_gazebo bash -c "source /opt/ros/humble/setup.bash && ros2 topic list 2>/dev/null" | grep -q "/LocoApiTopicReq"; do
    sleep 1
done

echo "✅ K1-INTERFACE ERKANNT! Führe DDS Warm-Up durch..."
# Kurzes Listening auf LocoApiTopicResp um die Route zu stabilisieren
docker exec -i r2k_unify2_gazebo bash -c "source /opt/ros/humble/setup.bash && source /root/ros2k_unify2/ros2_ws/install/setup.bash && ros2 topic echo --once /LocoApiTopicResp" 2>/dev/null &
~~~

**[NEW in v5] Hybrid OS Warm-Up:**
The K1 interface check is now integrated into the central Hybrid OS deployment script, executing the probe natively on Ubuntu 22.04 or via Docker on Ubuntu 24.04.
~~~bash
# snippet from launch_r2k.sh
if [ "$K1_READY" = false ] && ros2 topic list 2>/dev/null | grep -q "/bot1/LocoApiTopicReq"; then
    echo "🦾 K1-Interface erkannt! Stabilisiere Route..."
    if [ "$UBUNTU_VERSION" == "22.04" ]; then
        ros2 topic echo --once /bot1/LocoApiTopicResp > /dev/null 2>&1 &
    else
        docker exec -i $CONTAINER_NAME bash -c "$SOURCE_CMD && ros2 topic echo --once /bot1/LocoApiTopicResp > /dev/null 2>&1" &
    fi
    K1_READY=true
fi
~~~

## 4. Known Issues & Limitations
* The transition from `Stand` to `Trot` incurs a physical delay, which severely impacts the biped's ability to react to sudden changes in the LLM strategy.
* If the RPC topic drops a command during a high-speed trot, the biped will attempt to abruptly stop or lose balance, usually resulting in a physical fall.
* **[NEW in v5] Namespace Mismatch:** The native SDK defaults to global topics (e.g., `/LocoApiTopicReq`). The micro-ROS agent must explicitly remap this into the `/bot1/` namespace to prevent collisions with other bipeds on the network.

## 5. Glossary
* **RPC (Remote Procedure Call):** A protocol where a program executes a subroutine in another address space. Here, sending string commands to change the robot's internal hardware state.
* **LocoAPI:** The proprietary locomotion interface provided by the Booster K1 SDK.
* **[NEW in v5] API Code 2000:** The K1 command code indicating a transition to a stationary, balanced standing pose.
* **[NEW in v5] API Code 2001:** The K1 command code executing active dynamic locomotion based on the payload's velocity parameters.
