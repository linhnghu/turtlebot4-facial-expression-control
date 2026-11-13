import math

import pytest

from turtlebot4_emotion.core import Config, Controller
from turtlebot4_emotion.perception import detection_from_results


def ready(label='happy'):
    c = Controller()
    for t in (0., .31, .62):
        c.odometry(0, 0, 0, t)
        c.observe(label, .95, 1, t, t)
    return c


@pytest.mark.parametrize('label,linear,angular', [
    ('happy', .1, .45), ('sad', .1, -.45), ('neutral', 0, 0),
    ('angry', -.1, 0), ('surprise', 0, .45), ('fear', .1, 0),
])
def test_six_mappings(label, linear, angular):
    assert ready(label).tick(.62) == (linear, angular)


def test_requires_stable_expression_and_odometry():
    c = Controller()
    c.observe('happy', .99, 1, 0, 0)
    assert c.tick(0) == (0, 0)
    for t in (.31, .62):
        c.observe('happy', .99, 1, t, t)
    assert c.tick(.62) == (0, 0)
    assert c.reason == 'waiting_for_odometry'


@pytest.mark.parametrize('label,confidence,faces', [
    ('happy', .1, 1), ('happy', .99, 0), ('happy', .99, 2),
    ('disgust', .99, 1), ('unknown', .99, 1), ('happy', float('nan'), 1),
])
def test_bad_perception_stops(label, confidence, faces):
    c = ready()
    c.observe(label, confidence, faces, .7, .7)
    assert c.tick(.7) == (0, 0)


def test_neutral_stops_immediately_even_at_low_confidence():
    c = ready()
    c.observe('neutral', .2, 1, .7, .7)
    assert c.tick(.7) == (0, 0)


def test_stale_and_future_results_and_replays_stop():
    for stamp, now in ((.7, 4), (4, .7), (.6, .7)):
        c = ready()
        c.observe('happy', .99, 1, stamp, now)
        assert c.tick(now) == (0, 0)


def test_camera_timeout_and_odometry_timeout():
    c = ready()
    c.odometry(0, 0, 0, 2.2)
    assert c.tick(2.2) == (0, 0)
    c = ready()
    assert c.tick(1.3) == (0, 0)
    assert c.reason == 'odometry_timeout'


def test_arc_finishes_and_does_not_repeat_until_stable_neutral():
    c = ready()
    for t in (1., 2., 3., 3.7, 4.4):
        c.odometry(0, 0, 0, t)
        c.observe('happy', .99, 1, t, t)
        c.tick(t)
    assert c.action is None
    for t in (5., 5.31, 5.62):
        c.odometry(0, 0, 0, t)
        c.observe('neutral', .8, 1, t, t)
    for t in (6., 6.31, 6.62):
        c.odometry(0, 0, 0, t)
        c.observe('happy', .99, 1, t, t)
    assert c.tick(6.62)[0] > 0


@pytest.mark.parametrize('label,direction', [('fear', 1), ('angry', -1)])
def test_step_uses_measured_distance(label, direction):
    c = ready(label)
    c.odometry(.11*direction, 0, 0, .7)
    assert c.tick(.7)[0] * direction > 0
    c.odometry((.13 if label == 'angry' else .21)*direction, 0, 0, .8)
    assert c.tick(.8) == (0, 0)
    assert c.reason == 'completed'


def test_surprise_uses_unwrapped_odometry_for_full_turn():
    c = ready('surprise')
    for i in range(1, 65):
        t, yaw = .62 + i*.1, i*.1
        c.odometry(0, 0, math.atan2(math.sin(yaw), math.cos(yaw)), t)
        c.observe('surprise', .99, 1, t, t)
        c.tick(t)
    assert c.angle >= 2*math.pi - .04
    assert c.action is None
    assert c.reason == 'completed'


def test_stalled_robot_hits_deadline():
    c = ready('surprise')
    for i in range(1, 311):
        t = .62 + i*.1
        c.odometry(0, 0, 0, t)
        c.observe('surprise', .99, 1, t, t)
        c.tick(t)
    assert c.action is None
    assert c.reason == 'motion_timeout'


def test_emergency_stop_reset_requires_neutral():
    c = ready()
    c.emergency_stop()
    assert c.tick(.62) == (0, 0)
    c.reset()
    for t in (1., 1.31, 1.62):
        c.odometry(0, 0, 0, t)
        c.observe('fear', .99, 1, t, t)
    assert c.tick(1.62) == (0, 0)


def test_stop_latch_survives_missing_perception():
    c = Controller()
    c.emergency_stop()
    assert c.tick(100.) == (0, 0)
    assert c.latched and c.reason == 'emergency_stop'


def test_no_face_gap_breaks_stability():
    c = Controller()
    c.odometry(0, 0, 0, 0)
    c.observe('happy', .9, 1, 0, 0)
    c.observe('happy', .9, 1, .3, .3)
    c.tick(2.)
    c.odometry(0, 0, 0, 2.1)
    c.observe('happy', .9, 1, 2.1, 2.1)
    assert c.tick(2.1) == (0, 0)


def test_odom_jump_and_nan_stop():
    c = ready()
    c.odometry(1., 0, 0, .7)
    assert c.tick(.7) == (0, 0)
    c = ready()
    c.odometry(float('nan'), 0, 0, .7)
    assert c.tick(.7) == (0, 0)


def test_deepface_keeps_unsupported_dominant_emotion():
    result = detection_from_results([{'emotion': {'disgust': 90., 'happy': 10.},
                                     'region': {'x': 1, 'y': 2, 'w': 3, 'h': 4}}], 1.)
    assert result['emotion'] == 'disgust'
    assert result['confidence'] == .9
    assert detection_from_results([], 1.)['faces'] == 0
    assert detection_from_results([{}, {}], 1.)['emotion'] == 'unknown'


@pytest.mark.parametrize('kwargs', [{'linear_speed': .5}, {'confidence': 2},
                                   {'stable_time': -1}, {'input_timeout': float('nan')}])
def test_invalid_configuration_rejected(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs)
