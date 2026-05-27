1. deploy_relay.sh (The Setup & Installation Script)

This is your primary tool. It copies all necessary files to the robot, configures the systemd background services, dynamically updates the robot's namespace prefix, and optionally sets the bridge to launch automatically every time the robot powers on.
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

    ./deploy_relay.sh 10.42.0.102 bot1

    (Deploys to 10.42.0.102, prefixes topics with /bot1/, and sets the bridge to run on boot).

    Deploy for Testing (No Auto-Start):
    Bash

    ./deploy_relay.sh --no_auto_start 10.42.0.102 bot_test

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

    ./start_relays.sh 10.42.0.102 bot2

    (Connects, sets the environment variables, starts the Python scripts in the background, and drops internal_relay.log and external_relay.log in the robot's workspace).

3. stop_relays.sh (The Manual Kill Script)

This script is the exact counter-part to start_relays.sh. It logs into the robot and forcefully kills any running Python processes named internal_relay.py or external_relay.py.
Parameters (Positional Arguments)

    <Robot_IP>: The IP address of the robot. (It does not need the <Robot_Name> because it just searches for the script names).

Examples

    Stop the manually started relays:
    Bash

    ./stop_relays.sh 10.42.0.102

    (Silently kills the background processes on that robot).

A quick tip for your workflow: If you decide to stick with the systemd approach (which is highly recommended for a stable fleet), you can safely delete start_relays.sh and stop_relays.sh to prevent accidental conflicts.