"""Independent 20 Hz velocity publisher and perception watchdog."""
import json
import math
import signal
import time

import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from std_srvs.srv import Trigger

from .core import Config, Controller


class EmotionController(Node):
    def __init__(self):
        super().__init__('emotion_controller')
        defaults = Config()
        params = {k: self.declare_parameter(k, v).value for k, v in vars(defaults).items()}
        self.core = Controller(Config(**params))
        self.velocity = self.create_publisher(Twist, '/cmd_vel', 1)
        self.status = self.create_publisher(String, '/emotion/status', 1)
        self.create_subscription(String, '/emotion/detection', self.detection, 1)
        self.create_subscription(Odometry, '/odom', self.odom, qos_profile_sensor_data)
        self.create_service(Trigger, '/emotion/stop', self.stop)
        self.create_service(Trigger, '/emotion/reset', self.reset)
        self.timer = self.create_timer(.05, self.update, clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.last_reason = None

    def detection(self, msg):
        try:
            item = json.loads(msg.data)
            if type(item['faces']) is not int or not isinstance(item['emotion'], str):
                raise ValueError('invalid detection fields')
            self.core.observe(item['emotion'], float(item['confidence']), item['faces'],
                              float(item['captured_at']), time.monotonic())
        except (ValueError, TypeError, KeyError, OverflowError):
            self.core.invalidate('malformed_detection')
        self.update()

    def odom(self, msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        norm = math.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w)
        if not math.isfinite(norm) or abs(norm - 1) > .05:
            self.core.odometry(float('nan'), 0, 0, time.monotonic())
            return
        yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z))
        self.core.odometry(p.x, p.y, yaw, time.monotonic())

    def stop(self, request, response):
        self.core.emergency_stop()
        self.update()
        response.success, response.message = True, 'Stopped; reset then show Neutral to rearm.'
        return response

    def reset(self, request, response):
        self.core.reset()
        self.update()
        response.success, response.message = True, 'Show stable Neutral to rearm.'
        return response

    def update(self):
        linear, angular = self.core.tick(time.monotonic())
        msg = Twist()
        msg.linear.x, msg.angular.z = linear, angular
        self.velocity.publish(msg)
        data = dict(action=self.core.action, reason=self.core.reason,
                    linear=linear, angular=angular, distance=self.core.distance,
                    angle=self.core.angle, stopped=self.core.latched)
        self.status.publish(String(data=json.dumps(data)))
        if self.core.reason != self.last_reason:
            self.get_logger().info(self.core.reason)
            self.last_reason = self.core.reason


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = EmotionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if rclpy.ok():
            for _ in range(3):
                node.velocity.publish(Twist())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
