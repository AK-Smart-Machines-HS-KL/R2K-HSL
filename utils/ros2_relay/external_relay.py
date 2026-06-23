import sys
import argparse
import socket
import threading
import rclpy
from rclpy.node import Node
from rclpy.serialization import serialize_message, deserialize_message

from booster_msgs.msg import RpcReqMsg
from booster_msgs.msg import RpcRespMsg

# =====================================================================
# TODO: Update this import to match the actual message type used by 
# the /odometer_state topic on your robot.
# =====================================================================
from booster_interface.msg import Odometer as OdomMsg

# UDP Ports for the "Airgap"
PORT_REQ = 6000  # Sending Requests to internal
PORT_RESP = 6001 # Receiving Responses from internal
PORT_ODOM = 6002 # Receiving Odometer from internal

class ExternalRelayNode(Node):
    def __init__(self, prefix: str):
        super().__init__(f'external_fleet_relay_{prefix}')
        prefix = prefix.strip('/')
        
        # ROS Setup
        self.sub_req = self.create_subscription(RpcReqMsg, f'/{prefix}/LocoApiTopicReq', self.req_callback, 10)
        
        self.pub_resp = self.create_publisher(RpcRespMsg, f'/{prefix}/LocoApiTopicResp', 10)
        self.pub_odom = self.create_publisher(OdomMsg, f'/{prefix}/odometer_state', 10)

        # Socket Setup (Send to Internal)
        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Socket Setup (Receive Responses from Internal)
        self.sock_recv_resp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv_resp.bind(('127.0.0.1', PORT_RESP))

        # Socket Setup (Receive Odometer from Internal)
        self.sock_recv_odom = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv_odom.bind(('127.0.0.1', PORT_ODOM))

        # Start threads to listen for incoming UDP traffic
        self.listen_thread_resp = threading.Thread(target=self.udp_listener_resp, daemon=True)
        self.listen_thread_resp.start()

        self.listen_thread_odom = threading.Thread(target=self.udp_listener_odom, daemon=True)
        self.listen_thread_odom.start()

        self.get_logger().info(f'External Relay Active: Bridging /{prefix}/... to Fleet.')

    def req_callback(self, msg):
        # Forward Request from Fleet to internal node
        serialized_msg = serialize_message(msg)
        self.sock_send.sendto(serialized_msg, ('127.0.0.1', PORT_REQ))

    def udp_listener_resp(self):
        # Listen for Responses from internal node and publish to Fleet
        while True:
            try:
                data, _ = self.sock_recv_resp.recvfrom(65535)
                msg = deserialize_message(data, RpcRespMsg)
                self.pub_resp.publish(msg)
            except Exception as e:
                self.get_logger().error(f"UDP Recv Error (Resp): {e}")

    def udp_listener_odom(self):
        # Listen for Odometer from internal node and publish to Fleet
        while True:
            try:
                data, _ = self.sock_recv_odom.recvfrom(65535)
                msg = deserialize_message(data, OdomMsg)
                self.pub_odom.publish(msg)
            except Exception as e:
                self.get_logger().error(f"UDP Recv Error (Odom): {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('prefix', type=str)
    parsed_args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)
    node = ExternalRelayNode(parsed_args.prefix)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
