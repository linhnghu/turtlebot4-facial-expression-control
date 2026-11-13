#!/usr/bin/env python3
"""Synthetic ROS inputs and actual Gazebo odometry; no recognition accuracy claim.

Start ./run_emotion_demo.bash camera:=false gazebo_gui:=false first, then run
source emotion_env.bash; python3 src/turtlebot4_emotion/test/check_gazebo.py
"""
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String


class Probe(Node):
    def __init__(self):
        super().__init__('emotion_runtime_probe')
        self.pub = self.create_publisher(String, '/emotion/detection', 1)
        self.create_subscription(Odometry, '/odom', self.odom_cb, qos_profile_sensor_data)
        self.create_subscription(Twist, '/cmd_vel', self.cmd_cb, 1)
        self.create_subscription(String, '/emotion/status', self.status_cb, 1)
        self.pose = None
        self.odom_time = 0.
        self.velocity = (0., 0.)
        self.status = {}
        self.yaw_total = 0.
        self.last_yaw = None
        self.report = []

    def odom_cb(self, msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z))
        if self.last_yaw is not None:
            self.yaw_total += math.atan2(math.sin(yaw-self.last_yaw), math.cos(yaw-self.last_yaw))
        self.last_yaw = yaw
        self.pose, self.odom_time = (p.x, p.y, yaw), time.monotonic()

    def cmd_cb(self, msg):
        self.velocity = (msg.linear.x, msg.angular.z)

    def status_cb(self, msg):
        self.status = json.loads(msg.data)

    def pump(self, duration, label=None, faces=1):
        end, next_send = time.monotonic()+duration, 0.
        while time.monotonic() < end:
            now = time.monotonic()
            if label is not None and now >= next_send:
                self.pub.publish(String(data=json.dumps(dict(
                    emotion=label, confidence=.99, faces=faces, captured_at=now))))
                next_send = now+.1
            rclpy.spin_once(self, timeout_sec=.02)

    def check(self, name, condition, **details):
        self.report.append(dict(check=name, passed=bool(condition), **details))
        print(json.dumps(self.report[-1]), flush=True)
        if not condition:
            raise AssertionError(name)

    def run(self):
        end = time.monotonic()+60
        while time.monotonic() < end and (self.pose is None or not self.status):
            self.pump(.1)
        self.check('odometry_and_controller_ready', self.pose is not None and bool(self.status))
        self.pump(1., 'neutral')
        self.check('neutral_zero', self.velocity == (0., 0.))
        for label in ('happy', 'sad', 'angry', 'fear', 'surprise'):
            self.pump(1., 'neutral')
            origin, initial_yaw = self.pose, self.yaw_total
            self.pump(1.2, label)
            v, w = self.velocity
            expected = {'happy': v > 0 and w > 0, 'sad': v > 0 and w < 0,
                        'angry': v < 0 and w == 0, 'fear': v > 0 and w == 0,
                        'surprise': v == 0 and w > 0}[label]
            self.check(label+'_cmd_vel', expected, linear=v, angular=w)
            end = time.monotonic()+32
            while time.monotonic() < end and self.status.get('action') is not None:
                self.pump(.1, label)
            self.pump(.3, label)
            self.check(label+'_completed', self.status.get('reason') == 'completed'
                       and self.velocity == (0., 0.), status=self.status)
            travel = math.hypot(self.pose[0]-origin[0], self.pose[1]-origin[1])
            turn = self.yaw_total-initial_yaw
            if label in ('happy', 'sad'):
                ok = travel > .10 and turn * (1 if label == 'happy' else -1) > .3
            elif label == 'surprise':
                ok = abs(turn - 2*math.pi) < .25
            else:
                heading = ((self.pose[0]-origin[0])*math.cos(origin[2])
                           + (self.pose[1]-origin[1])*math.sin(origin[2]))
                low, high = (.16, .28) if label == 'fear' else (.09, .17)
                ok = low < travel < high and heading * (1 if label == 'fear' else -1) > low-.02
            self.check(label+'_physical_odometry', ok, travel=travel, turn=turn)
            self.pump(.8, label)
            self.check(label+'_does_not_repeat', self.velocity == (0., 0.))
        self.pump(1., 'neutral')
        self.pump(1.2, 'happy')
        self.pump(.3, 'unknown', faces=0)
        self.check('no_face_stops', self.velocity == (0., 0.))
        self.pump(1., 'neutral')
        self.pump(1.2, 'sad')
        self.pump(1.8)
        self.check('camera_result_timeout_stops', self.velocity == (0., 0.))


def main():
    rclpy.init()
    node = Probe()
    try:
        node.run()
    finally:
        node.pump(.2, 'neutral')
        target = Path('artifacts/emotion/runtime_checks.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(node.report, indent=2)+'\n')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
