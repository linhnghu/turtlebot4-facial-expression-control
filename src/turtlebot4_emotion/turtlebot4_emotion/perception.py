"""Translate DeepFace output without treating a no-face image as a face."""
import math


def detection_from_results(results, captured_at):
    payload = dict(emotion='unknown', confidence=0., faces=len(results),
                   captured_at=captured_at, region=None)
    if len(results) != 1:
        return payload
    result = results[0]
    scores = result.get('emotion', {})
    if not scores:
        return payload
    # Keep all seven classes: disgust must never become the best of six others.
    label = max(scores, key=scores.get)
    score = float(scores[label]) / 100.
    if not math.isfinite(score) or not 0 <= score <= 1:
        return payload
    region = result.get('region')
    if region:
        region = {key: int(region[key]) for key in ('x', 'y', 'w', 'h')}
    payload.update(emotion=label, confidence=score, region=region)
    return payload
