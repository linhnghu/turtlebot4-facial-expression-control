#!/usr/bin/env python3
"""Smoke real DeepFace inference; this does not measure human emotion accuracy."""
import argparse
import json
from pathlib import Path
import time

import cv2
import numpy as np
from deepface import DeepFace

from turtlebot4_emotion.perception import detection_from_results


def infer(frame):
    start = time.monotonic()
    try:
        results = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=True,
                                   detector_backend='opencv', silent=True)
    except ValueError as exc:
        if 'Face could not be detected' not in str(exc):
            raise
        results = []
    result = detection_from_results(results, start)
    result['inference_seconds'] = time.monotonic()-start
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', help='Path to a single-face test image')
    parser.add_argument('--webcam', type=int, help='Capture and analyze 5 real webcam frames')
    args = parser.parse_args()
    DeepFace.build_model(task='facial_attribute', model_name='Emotion')
    report = []
    blank = infer(np.zeros((480, 640, 3), dtype=np.uint8))
    assert blank['faces'] == 0
    report.append(dict(check='blank_image_no_face', passed=True, **blank))
    if args.fixture:
        frame = cv2.imread(args.fixture)
        assert frame is not None, 'Cannot read fixture'
        single = infer(frame)
        assert single['faces'] == 1, single
        report.append(dict(check='single_face_inference', passed=True, **single))
        multi = infer(np.concatenate([frame, frame], axis=1))
        assert multi['faces'] == 2 and multi['emotion'] == 'unknown', multi
        report.append(dict(check='multiple_faces_inhibited', passed=True, **multi))
    if args.webcam is not None:
        camera = cv2.VideoCapture(args.webcam, cv2.CAP_V4L2)
        try:
            assert camera.isOpened(), 'Cannot open webcam'
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            for i in range(5):
                ok, frame = camera.read()
                assert ok, 'Cannot read webcam frame'
                result = infer(frame)
                report.append(dict(check=f'webcam_frame_{i}', passed=True, **result))
        finally:
            camera.release()
    target = Path('artifacts/emotion/perception_checks.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
