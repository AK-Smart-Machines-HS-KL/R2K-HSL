import subprocess
import time
import signal
import sys

def record_topics_for_duration():
    # Configuration
    DURATION = 15  # seconds
    OUTPUT_NAME = "booster_camera_recording"
    
    topics = [
        "/boostercamera/head/rgb",
        "/boostercamera/head/depth",
        "/boostercamera/head/rgb/camera_info"
    ]

    # Construct the command based on the ROS version
    # ROS 2 saves bags as a directory
    cmd = ["ros2", "bag", "record", "-o", OUTPUT_NAME] + topics

    print(f"Starting {ROS_VERSION} bag recording for {DURATION} seconds...")
    print(f"Command: {' '.join(cmd)}")
    
    # Start the recording process
    process = subprocess.Popen(cmd)

    try:
        # Keep the script alive for the specified duration
        time.sleep(DURATION)
    except KeyboardInterrupt:
        print("\nRecording interrupted by user early.")
    finally:
        print("\nTime's up! Stopping recording gracefully...")
        # Send SIGINT (Ctrl+C equivalent) so the bag file closes cleanly without corruption
        process.send_signal(signal.SIGINT)
        process.wait()
        print(f"Recording complete. Saved to: {OUTPUT_NAME}")

if __name__ == "__main__":
    record_topics_for_duration()
