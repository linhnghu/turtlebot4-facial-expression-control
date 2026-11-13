#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source ./emotion_env.bash
if ! ros2 pkg prefix turtlebot4_emotion >/dev/null 2>&1; then
    echo 'Build first: ./setup_emotion.bash' >&2
    exit 1
fi
exec ros2 launch turtlebot4_emotion emotion.launch.py "$@"
