#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source ./emotion_env.bash
/usr/bin/python3 -m venv --system-site-packages .venv-emotion
.venv-emotion/bin/python -m pip install --timeout 120 --retries 5 -r src/turtlebot4_emotion/requirements.txt
mkdir -p "$DEEPFACE_HOME"
export CUDA_VISIBLE_DEVICES=-1 TF_CPP_MIN_LOG_LEVEL=2
export TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1
.venv-emotion/bin/python - <<'PY'
from deepface import DeepFace
import cv2
import rclpy
DeepFace.build_model(task='facial_attribute', model_name='Emotion')
print(f'DeepFace emotion model and OpenCV {cv2.__version__} ready.')
PY
colcon build --symlink-install --packages-select turtlebot4_emotion
