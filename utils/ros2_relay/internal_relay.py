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
PORT_REQ = 6000  # Receiving Requests from external
PORT_RESP = 6001 # Sending Responses to external
PORT_ODOM = 6002 # Sending Odometer to external

class InternalRelayNode(Node):
    def __init__(self):
        super().__init__('internal_fleet_relay')
        
        # ROS Setup
        self.pub_req = self.create_publisher(RpcReqMsg, '/LocoApiTopicReq', 10)
        
        self.sub_resp = self.create_subscription(RpcRespMsg, '/LocoApiTopicResp', self.resp_callback, 10)
        self.sub_odom = self.create_subscription(OdomMsg, '/odometer_state', self.odom_callback, 10)

        # Socket Setup (Send to External)
        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Socket Setup (Receive from External)
        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv.bind(('127.0.0.1', PORT_REQ))

        # Start a thread to listen for incoming UDP requests
        self.listen_thread = threading.Thread(target=self.udp_listener_req, daemon=True)
        self.listen_thread.start()

        self.get_logger().info('Internal Relay Active: Isolated to robot network.')

    def resp_callback(self, msg):
        # Forward Response to external node
        serialized_msg = serialize_message(msg)
        self.sock_send.sendto(serialized_msg, ('127.0.0.1', PORT_RESP))

    def odom_callback(self, msg):
        # Forward Odometer to external node on dedicated port
        serialized_msg = serialize_message(msg)
        self.sock_send.sendto(serialized_msg, ('127.0.0.1', PORT_ODOM))

    def udp_listener_req(self):
        # Listen for Requests from external node and publish to robot
        while True:
            try:
                data, _ = self.sock_recv.recvfrom(65535) # Max local UDP packet size
                msg = deserialize_message(data, RpcReqMsg)
                self.pub_req.publish(msg)
            except Exception as e:
                self.get_logger().error(f"UDP Recv Error (Req): {e}")

def main():
    rclpy.init()
    node = InternalRelayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
