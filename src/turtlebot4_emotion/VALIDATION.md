# Kiểm chứng — 13/11/2026

Môi trường: Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress, TurtleBot 4 Lite.

## Bộ điều khiển

- `colcon build --symlink-install --packages-select turtlebot4_emotion`: thành công.
- `PYTHONPATH=src/turtlebot4_emotion python3 -m pytest -q src/turtlebot4_emotion/test`:
  30 kiểm thử logic thành công.
- `ign sdf -k src/turtlebot4_emotion/worlds/emotion_arena.sdf`: Valid.
- `bash -n` và compile Python: thành công.
- Launch `--show-args`: đọc được đầy đủ tham số.

## ROS và Gazebo

Chạy simulator không webcam, phát JSON biểu cảm tổng hợp bằng
`test/check_gazebo.py`, đo `/cmd_vel`, `/emotion/status` và `/odom`:
**24/24 kiểm tra thành công**.

| Hành động | Odometry đo được khi hoàn tất |
|---|---|
| Happy | Dịch chuyển khoảng 24.8 cm, quay trái 1.18 rad |
| Sad | Dịch chuyển khoảng 25.6 cm, quay phải 1.23 rad |
| Angry | Lùi khoảng 12.7 cm |
| Fear | Tiến khoảng 20.8 cm |
| Surprise | Quay 6.265 rad, khoảng 359° |
| Neutral | Vận tốc bằng 0 |

Đã kiểm tra không tự lặp khi giữ nguyên biểu cảm, dừng khi báo không có mặt,
và dừng khi ngừng nhận kết quả. Chi tiết máy đọc được tại
`artifacts/emotion/runtime_checks.json` tính từ gốc workspace.

Lần đầu thử lùi 20 cm, base Create 3 chặn ở giới hạn backup. Cấu hình cuối
dùng 12 cm; giữ nguyên bảo vệ của base. Độ dài cung dùng thời gian thực nên
quãng đường trong Gazebo phụ thuộc real-time factor của máy.

## Phạm vi nhận diện

Webcam `/dev/video0` mở được và đọc được ảnh 640×480. Kiểm tra này chỉ xác nhận
thiết bị hoạt động.

DeepFace 0.0.93 / TensorFlow 2.15.1 / OpenCV 4.10 đã nạp mô hình Emotion:
**8/8 kiểm tra suy luận thành công** (`artifacts/emotion/perception_checks.json`):

- Ảnh đen: không nhận thành khuôn mặt.
- Ảnh một mặt: trả nhãn biểu cảm, confidence và bounding box hợp lệ.
- Ảnh ghép hai mặt: phát hiện hai mặt, không phát nhãn điều khiển.
- 5 frame webcam thật: xử lý thành công; cảnh lúc thử không có khuôn mặt,
  kết quả `unknown`, `faces=0`.

Chạy node camera với cửa sổ hiển thị và controller trên topic vận tốc thử:
nhận 37 bản tin nhận diện và 257 bản tin trạng thái trong cửa sổ thử, không
có vận tốc khác 0. Bản tin cuối nhận nhãn `neutral` với một khuôn mặt và
confidence khoảng 0.935. Đây là kết quả mô hình trả về, không phải nhãn do
người đánh giá xác nhận. Xem `artifacts/emotion/live_node_smoke.json`.
Đã chạy lại với NumPy 1.24.4 phù hợp SciPy hệ thống: 8/8 kiểm tra suy luận
vẫn qua. Phiên có cửa sổ webcam kết thúc sạch cả camera và controller bằng
SIGINT/Ctrl+C, không còn process demo chạy sau kiểm tra.

Fixture một mặt là ảnh astronaut đi kèm scikit-image v0.22.0, tải tạm để thử;
không lưu ảnh webcam hoặc fixture vào mã nguồn/artifacts. Kiểm tra fixture
không khẳng định nhãn biểu cảm dự đoán là đúng. Có thể chạy lại với ảnh riêng:

```bash
source emotion_env.bash
CUDA_VISIBLE_DEVICES=-1 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1 \
  .venv-emotion/bin/python src/turtlebot4_emotion/test/check_perception.py \
  --fixture /duong/dan/anh_mot_mat.png --webcam 0
```

Kết quả ROS/Gazebo phía trên dùng nhãn tổng hợp, không đo
độ chính xác nhận diện biểu cảm. Chưa thực hiện bộ thử người dùng có nhãn cho
cả sáu biểu cảm; chưa kiểm chứng chuyển động trên TurtleBot thật.
