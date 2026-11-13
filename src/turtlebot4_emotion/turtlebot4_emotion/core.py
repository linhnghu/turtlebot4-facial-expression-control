"""ROS-independent motion policy; all deadlines use monotonic wall time."""
from dataclasses import dataclass
import math


EMOTIONS = {'happy', 'sad', 'neutral', 'angry', 'surprise', 'fear'}


@dataclass
class Config:
    confidence: float = 0.65
    stable_time: float = 0.6
    min_samples: int = 3
    input_timeout: float = 1.5
    odom_timeout: float = 0.6
    linear_speed: float = 0.10
    angular_speed: float = 0.45
    arc_duration: float = 3.0
    step_distance: float = 0.20
    reverse_distance: float = 0.12
    motion_timeout: float = 30.0

    def __post_init__(self):
        for name, value in vars(self).items():
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be finite and positive')
        if self.confidence > 1 or self.linear_speed > .20 or self.angular_speed > .8:
            raise ValueError('confidence <= 1, linear_speed <= .20, angular_speed <= .8 required')


class Controller:
    def __init__(self, config=None):
        self.cfg = config or Config()
        self.action = None
        self.reason = 'waiting_for_face'
        self.last_trigger = None
        self.candidate = None
        self.samples = 0
        self.since = 0.
        self.observed = None
        self.last_capture = float('-inf')
        self.last_odom = None
        self.pose = None
        self.distance = self.angle = 0.
        self.started = 0.
        self.latched = False

    def stop(self, reason):
        self.action = None
        self.reason = reason

    def emergency_stop(self):
        self.latched = True
        self.stop('emergency_stop')

    def reset(self):
        self.latched = False
        self.last_trigger = 'blocked'
        self.candidate = None
        self.samples = 0
        self.stop('show_neutral_to_rearm')

    def invalidate(self, reason):
        self.observed = None
        self.candidate = None
        self.samples = 0
        self.stop(reason)

    def observe(self, label, confidence, faces, captured_at, now):
        if (not all(math.isfinite(v) for v in (confidence, captured_at, now))
                or not 0 <= confidence <= 1 or captured_at > now + .05
                or now - captured_at > self.cfg.input_timeout):
            self.invalidate('invalid_or_stale_result')
            return
        if captured_at <= self.last_capture:
            self.invalidate('out_of_order_result')
            return
        self.last_capture = captured_at
        if faces != 1 or label not in EMOTIONS or (label != 'neutral' and confidence < self.cfg.confidence):
            self.invalidate('no_single_confident_face')
            return
        # A gap between results must break stability even without intervening ticks.
        if self.observed is None or captured_at - self.observed > self.cfg.input_timeout:
            self.candidate = None
            self.samples = 0
        self.observed = captured_at
        if label != self.candidate:
            self.candidate, self.since, self.samples = label, now, 0
        self.samples += 1
        if self.action and label != self.action:
            self.stop('expression_changed')
        if label == 'neutral':
            self.stop('neutral')
        if self.latched:
            self.stop('emergency_stop')
            return
        if self.samples < self.cfg.min_samples or now - self.since < self.cfg.stable_time:
            return
        if label == 'neutral':
            self.last_trigger = None
            return
        if self.last_trigger == 'blocked' or label == self.last_trigger or self.action:
            return
        if self.last_odom is None or now - self.last_odom > self.cfg.odom_timeout:
            self.stop('waiting_for_odometry')
            return
        self.action = self.last_trigger = label
        self.started = now
        self.distance = self.angle = 0.
        self.reason = 'moving_' + label

    def odometry(self, x, y, yaw, now):
        if not all(math.isfinite(v) for v in (x, y, yaw, now)):
            self.last_odom = None
            self.stop('invalid_odometry')
            return
        if self.pose is not None and self.last_odom is not None:
            dx = math.hypot(x - self.pose[0], y - self.pose[1])
            dyaw = math.atan2(math.sin(yaw - self.pose[2]), math.cos(yaw - self.pose[2]))
            if dx > .25 or abs(dyaw) > .8:
                self.stop('odometry_jump')
            elif self.action:
                self.distance += dx
                self.angle += dyaw
        self.pose, self.last_odom = (x, y, yaw), now

    def tick(self, now):
        if self.latched:
            self.stop('emergency_stop')
            return 0., 0.
        if self.observed is None or now - self.observed > self.cfg.input_timeout:
            self.invalidate('face_timeout')
        if self.action and (self.last_odom is None or now - self.last_odom > self.cfg.odom_timeout):
            self.stop('odometry_timeout')
        if not self.action or self.latched:
            return 0., 0.
        elapsed = now - self.started
        if elapsed >= self.cfg.motion_timeout:
            self.stop('motion_timeout')
        elif self.action in ('happy', 'sad') and elapsed >= self.cfg.arc_duration:
            self.stop('completed')
        elif self.action in ('angry', 'fear') and self.distance >= (
                self.cfg.reverse_distance if self.action == 'angry' else self.cfg.step_distance):
            self.stop('completed')
        elif self.action == 'surprise' and self.angle >= 2 * math.pi - .04:
            self.stop('completed')
        if self.action == 'happy':
            return self.cfg.linear_speed, self.cfg.angular_speed
        if self.action == 'sad':
            return self.cfg.linear_speed, -self.cfg.angular_speed
        if self.action == 'angry':
            return -self.cfg.linear_speed, 0.
        if self.action == 'fear':
            return self.cfg.linear_speed, 0.
        if self.action == 'surprise':
            return 0., self.cfg.angular_speed
        return 0., 0.
