# Bài thực hành — Nhận diện biểu cảm khuôn mặt và điều khiển TurtleBot

Đã triển khai trong package riêng
[`turtlebot4_emotion`](src/turtlebot4_emotion/README.md).

```bash
cd ~/ros2_ws
./setup_emotion.bash
./run_emotion_demo.bash
```

Lệnh chạy mở Gazebo với TurtleBot 4 và webcam thật. Happy → cong trái;
Sad → cong phải; Neutral → dừng; Angry → lùi 0.12 m;
Surprise → xoay một vòng theo odometry; Fear → tiến 0.20 m.

Giữ biểu cảm ổn định để chạy một lần, đưa về Neutral trước khi lặp lại.
Nhấn Q/Esc hoặc Ctrl+C để kết thúc. Xem tài liệu package để chọn camera,
chạy với robot có sẵn, đổi tham số và dùng dịch vụ dừng.
