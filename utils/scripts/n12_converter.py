import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import numpy as np
import cv2
from cv_bridge import CvBridge

class NV12Converter(Node):
    def __init__(self):
        super().__init__('nv12_converter')
        
        # Subscribe to the original NV12 topic
        self.subscription = self.create_subscription(
            Image,
            '/boostercamera/head/rgb',
            self.image_callback,
            10)
            
        # Publish to a new topic that rqt_image_view can read
        self.publisher = self.create_publisher(
            Image, 
            '/boostercamera/head/rgb_converted', 
            10)
            
        self.bridge = CvBridge()
        self.get_logger().info("NV12 to RGB converter is running...")

    def image_callback(self, msg):
        if msg.encoding != 'nv12':
            self.get_logger().warn(f"Expected nv12 encoding, but got {msg.encoding}")
            return

        try:
            # NV12 image data size is (Height * Width * 1.5) bytes
            # 1. Convert the raw bytes directly into a 1D numpy array
            raw_data = np.frombuffer(msg.data, np.uint8)
            
            # 2. Reshape the array into the specific shape OpenCV requires for NV12
            yuv_img = raw_data.reshape((int(msg.height * 1.5), msg.width))
            
            # 3. Convert NV12 to standard RGB
            rgb_img = cv2.cvtColor(yuv_img, cv2.COLOR_YUV2RGB_NV12)
            
            # 4. Convert back to a ROS Image message and publish it
            rgb_msg = self.bridge.cv2_to_imgmsg(rgb_img, encoding="rgb8")
            rgb_msg.header = msg.header # Maintain the original timestamp
            
            self.publisher.publish(rgb_msg)
            
        except Exception as e:
            self.get_logger().error(f"Failed to convert image: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = NV12Converter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
