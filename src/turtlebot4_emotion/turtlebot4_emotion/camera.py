"""Live preview and latest-frame-only DeepFace worker (no queued old commands)."""
import json
import signal
import threading
import time

import cv2
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String

from .perception import detection_from_results


class Camera(Node):
    def __init__(self):
        super().__init__('emotion_camera')
        self.index = self.declare_parameter('camera_index', 0).value
        self.show = self.declare_parameter('show_window', True).value
        self.interval = self.declare_parameter('inference_interval', .15).value
        self.timeout = self.declare_parameter('input_timeout', 1.5).value
        self.publisher = self.create_publisher(String, '/emotion/detection', 1)
        self.create_subscription(String, '/emotion/status', self.status_cb, 1)
        self.status = 'waiting_for_controller'
        self.lock = threading.Lock()
        self.latest = None
        self.result = None
        self.halt = threading.Event()
        self.error = ''

    def status_cb(self, msg):
        self.status = json.loads(msg.data).get('reason', '')

    def publish(self, result):
        self.publisher.publish(String(data=json.dumps(result)))

    def infer(self):
        try:
            from deepface import DeepFace
            DeepFace.build_model(task='facial_attribute', model_name='Emotion')
            last = -1.
            while not self.halt.is_set():
                with self.lock:
                    sample = self.latest
                if sample is None or sample[0] == last:
                    self.halt.wait(.02)
                    continue
                last, frame = sample
                try:
                    results = DeepFace.analyze(frame, actions=['emotion'],
                        detector_backend='opencv', enforce_detection=True, silent=True)
                    result = detection_from_results(results, last)
                except ValueError as exc:
                    # DeepFace raises ValueError on no face. Other failures must
                    # surface rather than masquerade as valid classifications.
                    if 'Face could not be detected' not in str(exc):
                        raise
                    result = detection_from_results([], last)
                if time.monotonic() - last > self.timeout:
                    result.update(emotion='unknown', confidence=0.)
                with self.lock:
                    self.result = result
                if not self.halt.is_set() and rclpy.ok():
                    self.publish(result)
                self.halt.wait(max(.01, self.interval))
        except Exception as exc:
            self.error = f'{type(exc).__name__}: {exc}'
            self.get_logger().error(self.error)
            self.halt.set()

    def run(self):
        capture = cv2.VideoCapture(self.index, cv2.CAP_V4L2)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f'Cannot open webcam {self.index}')
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        worker = threading.Thread(target=self.infer, daemon=True)
        worker.start()
        window = 'TurtleBot - Facial expressions | Q / Esc: stop and exit'
        try:
            while rclpy.ok() and not self.halt.is_set():
                ok, frame = capture.read()
                captured = time.monotonic()
                if not ok:
                    raise RuntimeError('Webcam frame stream lost')
                with self.lock:
                    self.latest = (captured, frame.copy())
                    result = self.result
                rclpy.spin_once(self, timeout_sec=0.)
                if self.show:
                    age = captured - result['captured_at'] if result else float('inf')
                    text = 'Loading DeepFace / waiting for result'
                    if result:
                        text = f"{result['emotion']}: {result['confidence']:.0%} | faces={result['faces']} | {age:.2f}s"
                        region = result.get('region')
                        if region and age <= self.timeout:
                            x, y, w, h = (int(region[k]) for k in ('x', 'y', 'w', 'h'))
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 220, 0), 2)
                    cv2.putText(frame, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, .52, (0, 255, 255), 1)
                    cv2.putText(frame, self.status, (10, 52), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 255, 255), 1)
                    cv2.putText(frame, 'Neutral: stop/rearm | hold expression for one action',
                                (10, frame.shape[0]-15), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
                    cv2.imshow(window, frame)
                    if cv2.waitKey(1) & 0xFF in (27, ord('q')):
                        break
                    if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                        break
            if self.error:
                raise RuntimeError(self.error)
        finally:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            self.halt.set()
            capture.release()
            worker.join(timeout=2.)
            if rclpy.ok():
                self.publish(detection_from_results([], time.monotonic()))
                time.sleep(.1)
            cv2.destroyAllWindows()


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = Camera()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
