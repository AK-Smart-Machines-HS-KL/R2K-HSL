# ROS 2 Relay

ROS 2 relay pair that isolates each K1 robot's topics into a fleet-facing namespace (`/<prefix>/...`) and bridges them to robot-local topics via UDP. Runs entirely on the K1 as two systemd services.

## Files

| File | Description |
|---|---|
| `deploy_relay.sh` | Deploys the relay pair to a K1 robot. Copies Python nodes + systemd units, substitutes the robot name prefix, installs services, and optionally enables auto-start on boot. Usage: `./deploy_relay.sh [OPTIONS] <Robot_IP> <Robot_Name>`. Options: `--no_auto_start` (install only). |
| `start_relays.sh` | Manual launch via SSH + nohup (no systemd). For debugging only — do not use alongside the systemd services (port conflict). Usage: `./start_relays.sh <Robot_IP> <Robot_Name>`. |
| `stop_relays.sh` | Kills manually started relay processes. Usage: `./stop_relays.sh <Robot_IP>`. |
| `external_relay.py` | External relay node (fleet-facing side). Subscribes host-side `/<prefix>/...` topics, serializes messages, sends via UDP to the internal relay. Publishes responses/odom received from the internal relay back to the fleet namespace. |
| `internal_relay.py` | Internal relay node (robot-local side). Receives UDP datagrams from the external relay, deserializes, and publishes to robot-local topics (`/LocoApiTopicReq`, `/GoToBallAndKick`). Subscribes robot-local response/odom topics and sends them back via UDP. |
| `system/external-relay.service` | systemd unit for the external relay. |
| `system/internal-relay.service` | systemd unit for the internal relay. |
| `system/99-relay-restart.sh` | NetworkManager dispatcher script — restarts both relay services when wlan0 joins the maker4 network. Fixes FastDDS interface capture at process startup. |

## Deployment

### Prerequisites

- K1 powered on, connected to the maker4 (or any other network) network (wlan AP hosted by the dev PC)
- SSH access to the robot (`booster@<Robot_IP>`)

### Standard deployment

```bash
./deploy_relay.sh 10.42.0.122 Kev1n
```

Deploys to the given IP, prefixes all fleet topics with `/Kev1n/`, and enables auto-start on boot.
Names the Bot for another name change Kev1n to \<robot_Name\>

### No auto-start (for testing)

```bash
./deploy_relay.sh --no_auto_start 10.42.0.122 Kev1n
```

Installs and configures the services but does not enable them. Start manually:

```bash
ssh booster@10.42.0.122 sudo systemctl start internal-relay external-relay
```

### Verification

```bash
# On the host (maker4 PC):
ros2 topic list | grep Kev1n
# Expect: /Kev1n/LocoApiTopicReq, /Kev1n/LocoApiTopicResp, /Kev1n/GoToBallAndKick
```

## Relayed Topics

### LocoApiTopicReq / LocoApiTopicResp

| Direction | Fleet Topic | Robot-Local Topic | Type | UDP Port |
|---|---|---|---|---|
| Host → Robot | `/<prefix>/LocoApiTopicReq` | `/LocoApiTopicReq` | `booster_msgs/RpcReqMsg` | 6000 |
| Robot → Host | `/<prefix>/LocoApiTopicResp` | `/LocoApiTopicResp` | `booster_msgs/RpcRespMsg` | 6001 |

Carries all K1 low-level RPC calls (Move, ChangeMode, RotateHead, VisualKick, etc.). The bridge publishes `RpcReqMsg` with `api_id` in the JSON header and parameters in the JSON body.

### GoToBallAndKick

| Direction | Fleet Topic | Robot-Local Topic | Type | UDP Port |
|---|---|---|---|---|
| Host → Robot | `/<prefix>/GoToBallAndKick` | `/GoToBallAndKick` | `k1_skills_msgs/GoToBallAndKickCmd` | 6004 |

High-level kick command from the host bridge to the on-robot `GoToBallAndKick` node (`utils/skills/goToBallAndKick.py`). The node closes the loop locally (vision → brain/Kick stream → vendor controller).

### Odometer

| Direction | Fleet Topic | Robot-Local Topic | Type | UDP Port |
|---|---|---|---|---|
| Robot → Host | `/<prefix>/odometer_state` | `/odometer_state` | `booster_interface/Odometer` | 6002 |

Relays the K1's wheel odometry (x/y/theta) to the fleet namespace. Requires `booster_interface` to be colcon-built and sourced on the robot — the topic is silent if the message type is not built (no subscriber can attach). See `core/docs/plans/v68_pre_ifa/k1_kick_head_vendor_audit.md` section 5.

## Modules

### external_relay.py

Fleet-facing relay node. Runs on the K1, subscribes `/<prefix>/...` topics from the host, and forwards them via UDP to the internal relay. Also receives responses/odom from the internal relay via UDP and publishes them back to the fleet namespace.

**Subscriptions:** `/<prefix>/LocoApiTopicReq`, `/<prefix>/GoToBallAndKick`
**Publishers:** `/<prefix>/LocoApiTopicResp`, `/<prefix>/odometer_state`
**UDP send:** port 6000 (Req), port 6004 (GoToBallAndKick)
**UDP recv:** port 6001 (Resp), port 6002 (Odometer)

Source chain (systemd): `/opt/ros/humble` + `BoosterRos2` + `BoosterRos2Interface` + `ros2_ws/install` (k1_skills_msgs).

### internal_relay.py

Robot-local relay node. Receives UDP datagrams from the external relay, deserializes, and publishes to robot-local topics. Subscribes robot-local response/odom topics and sends them back via UDP to the external relay.

**Publishers:** `/LocoApiTopicReq`, `/GoToBallAndKick`
**Subscriptions:** `/LocoApiTopicResp`, `/odometer_state`
**UDP recv:** port 6000 (Req), port 6004 (GoToBallAndKick)
**UDP send:** port 6001 (Resp), port 6002 (Odometer)

Source chain (systemd): same as external relay.

## Integration with ROS2K

For K1 control via the ROS2K bridge, the robot's relay entry in `core/src/relay/hardware_mirror.json` must match the prefix deployed here:

```json
"k1_bot": {"hardware_type": "k1", "topic": "/Kev1n/LocoApiTopicReq", "mirror_of": "blue_2"}
```