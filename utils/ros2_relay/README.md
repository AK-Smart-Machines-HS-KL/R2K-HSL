README, incl. Deployment on booster

This util will install and activate  a ROS2 
relay function to isolate each bots topic into its own namespace.

IMPORTANT: if you are to steer the K1 bots with ros2k core id (ollama_bridge), check the bots entries in core/src/relay/hardware_mirror.json:
Using Kev1n as running sample:
   "k1_bot": {"hardware_type": "k1", "topic": "/Kev1n/LocoApiTopicReq", "mirror_of": "blue_2"}
  }

NOTE:once we move the LLM into the K1 bots, this relay will render useless.

This is a loosely coupled set of python code. Main purposes:
* Runnning olllama bridge on host requires K1 listening 
* this code will list specific ros2 topics for DOMAIN 0
* Eg: K1<robot name>/<rLoCoAPITopicReq/>, <robot name>/Odometer_States
* refresh rate:
**  Installation**
0. Start network "maker4", nao12345
- PC maker4 provides the network wlan 
- K1 power on , will connect to the net, default mode will suffice
0. deploy_relay.sh <Robot_IP> <Robot_Name>
(The Setup & Installation Script)

This is your primary tool. It copies all necessary files to the robot, configures the system-daemon background services, dynamically updates the robot's ROS2 namespace prefix (robot name) , and optionally sets the relay to launch automatically every time the robot powers on

Parameters (Positional Arguments)

You must provide these two arguments in this exact order at the end of your command:

    <Robot_IP>: The current network IP address of the robot (e.g., 10.42.0.102). This is required so the script knows where to SSH into.

    <Robot_Name>: The unique namespace you want to assign to this specific robot (e.g., bot1, unitree_05, alpha). This string will be injected into the external-relay.service file to prefix the outgoing ROS 2 topics (creating /bot1/LocoApiTopicReq, etc.).

Options (Flags)

You can place these flags before the positional arguments to change how the script behaves:

    -h or --help: Prints a quick-reference guide in your terminal showing how to use the script, then exits without doing anything.

    --no_auto_start: By default, the script enables the systemd services to start on boot. If you use this flag, it skips that step. The services will be installed and configured, but you will have to start them manually via SSH (sudo systemctl start internal-relay.service). This is highly useful for testing a new robot configuration before committing to it permanently.

Examples

    Standard Full Deployment:
    Bash

    ./deploy_relay.sh 10.42.0.122 Kev1n
    password: 123456

    (Deploys to 10.42.0.122, prefixes topics with /Kev1n/, and sets the bridge to run on boot).
****************************
Shared connection to 10.42.0.122 closed.
Cleaning up SSH connection...
Exit request sent.
========================================================
Deployment Complete! The relays are now running.
========================================================

NOTE: deploy_relay.sh also installs a NetworkManager dispatcher script
(/etc/NetworkManager/dispatcher.d/99-relay-restart.sh) that automatically
restarts both relay services when wlan0 joins the maker4 network (10.42.x.x).
This fixes the issue where topics don't leave the bot if it boots in a
different network and joins maker4 later — FastDDS captures the interface
list at process startup, so the relays must restart to re-bind to wlan0.

****************************
    Deploy for Testing (No Auto-Start):
    Bash

    ./deploy_relay.sh --no_auto_start 10.42.0.122 Kev1n

    (Deploys the files and configures them for /bot_test/, but does NOT tell the robot to launch them automatically on the next reboot).

2. start_relays.sh (The Manual Launch Script)

This script is purely for manual, temporary execution (usually for debugging). It connects via SSH and runs the Python nodes in the background using nohup. It does not use systemd.

(Note: If you have already run deploy_relay.sh and the systemd services are active, do not run this script, as the ports will conflict).
Parameters (Positional Arguments)

    <Robot_IP>: The IP address of the robot.

    <Robot_Name>: The namespace prefix for the external relay.

Examples

    Start the relays manually:
    Bash

    ./start_relays.sh 10.42.0.122 Kev1n

    (Connects, sets the environment variables on robot to get relays active, starts the Python scripts in the background, and drops internal_relay.log and external_relay.log in the robot's workspace).
    
Check for "Kev1n"in ros2 topic list
3. stop_relays.sh <IP address>
(The Manual Kill Script)

This script is the exact counter-part to start_relays.sh. It logs into the robot and forcefully kills any running Python processes named internal_relay.py or external_relay.py.
Parameters (Positional Arguments)

    <Robot_IP>: The IP address of the robot. (It does not need the <Robot_Name> because it just searches for the script names).

Examples

    Stop the manually started relays:bridge
    Bash

    ./stop_relays.sh 10.42.0.122

    (Silently kills the background processes on that robot).

A quick tip for your workflow: If you decide to stick with the systemd approach (which is highly recommended for a stable fleet), you can safely delete start_relays.sh and stop_relays.sh to prevent accidental conflicts.