# Nhận diện biểu cảm khuôn mặt và điều khiển TurtleBot

Package ROS 2 Humble độc lập, dùng webcam thật → DeepFace/OpenCV → bộ lọc ổn
định → `/cmd_vel`. Launch mặc định mở TurtleBot 4 Lite trong Gazebo Fortress
và cửa sổ webcam; có thể dùng với robot đã có `/cmd_vel` và `/odom`.

## Chạy nhanh trong workspace này

```bash
cd ~/ros2_ws
./setup_emotion.bash
./run_emotion_demo.bash
```

Setup tạo `.venv-emotion` từ Python 3.10 hệ thống với `--system-site-packages`
để dùng được `rclpy`, cài phiên bản thư viện cố định và tải trọng số Emotion.
Không dùng `pip install` vào Python của ROS. Internet cần cho setup; chạy
nhận diện sau đó thực hiện cục bộ. Mô hình nằm trong `.models/emotion/.deepface`.
Nếu mới chuyển package sang workspace khác, cần cài ROS Humble, colcon và các
dependency trong `package.xml` trước; simulator TurtleBot 4 đã có ở workspace này.

Đợi robot xuất hiện và cửa sổ có kết quả nhận diện. Đưa một khuôn mặt vào
camera, đủ ánh sáng, nhìn gần chính diện. Giữ biểu cảm ít nhất 0.6 giây và
3 kết quả nhận diện hợp lệ. Neutral dừng ngay, không cần đợi ổn định.

| Biểu cảm | Chuyển động mặc định |
|---|---|
| Happy | Tiến 0.10 m/s, quay trái 0.45 rad/s trong 3 giây |
| Sad | Tiến 0.10 m/s, quay phải 0.45 rad/s trong 3 giây |
| Neutral | Dừng tại chỗ |
| Angry | Lùi khoảng 0.12 m, tốc độ 0.10 m/s |
| Surprise | Xoay trái một vòng, tốc độ 0.45 rad/s |
| Fear | Tiến khoảng 0.20 m, tốc độ 0.10 m/s |

Mỗi biểu cảm chỉ kích hoạt một lần. Muốn lặp cùng chuyển động, giữ Neutral ổn
định rồi biểu cảm lại. Một biểu cảm khác có thể kích hoạt sau khi ổn định;
đổi biểu cảm giữa chừng dừng chuyển động hiện tại trước. Mất mặt không tự cho
phép lặp lệnh cũ. Surprise cộng góc yaw liên tiếp từ `/odom`, có xử lý bước
qua ±π; Angry/Fear cộng quãng đường odometry. Sai số dừng phụ thuộc tần số
odometry, chu kỳ điều khiển và quán tính robot. Mọi chuyển động bị chặn sau
30 giây nếu robot không hoàn tất.

Quãng lùi 12 cm nằm dưới giới hạn backup của Create 3 trong mô phỏng; giữ nguyên
cơ chế bảo vệ của base. Khi đổi giới hạn quãng đường, cần kiểm tra lại với base.

Nhấn **Q**, **Esc**, đóng cửa sổ hoặc Ctrl+C để kết thúc. Cửa sổ hiển thị nhãn,
điểm số, số khuôn mặt, tuổi ảnh, trạng thái chuyển động và khung mặt. Điểm số
DeepFace không phải xác suất đúng đã hiệu chuẩn; nhãn biểu cảm không chứng
minh trạng thái cảm xúc bên trong của người dùng.

## Lựa chọn chạy

```bash
# Webcam khác; bỏ cửa sổ Gazebo nhưng giữ cửa sổ webcam
./run_emotion_demo.bash camera_index:=2 gazebo_gui:=false

# Chạy với TurtleBot đã khởi động, không tạo simulator
./run_emotion_demo.bash simulation:=false

# Remap nếu robot có namespace / kiểu tên topic khác
./run_emotion_demo.bash simulation:=false cmd_vel_topic:=/robot/cmd_vel odom_topic:=/robot/odom

# Kiểm tra controller bằng dữ liệu ROS tổng hợp, không bật webcam
./run_emotion_demo.bash camera:=false gazebo_gui:=false
```

Wrapper đặt `ROS_DOMAIN_ID=69`, `ROS_LOCALHOST_ONLY=1`, `IGN_PARTITION` riêng.
Terminal phụ cần `source ~/ros2_ws/emotion_env.bash`. Với robot thật qua LAN,
đặt `EMOTION_DOMAIN_ID` trùng domain của robot và `EMOTION_LOCALHOST_ONLY=0`
ở mọi terminal. Robot nhận `geometry_msgs/msg/Twist`; robot dùng TwistStamped
cần bộ chuyển đổi riêng. Chỉ chạy một nguồn điều khiển vận tốc trong cùng
domain; dừng Nav2, teleop hoặc demo khác trước khi chạy. Dùng vùng trống và
nút dừng của robot khi kiểm thử phần cứng. Bộ điều khiển này không tránh vật cản.

## ROS interface và dừng

| Interface | Kiểu | Nội dung |
|---|---|---|
| `/emotion/detection` | `std_msgs/msg/String` | JSON biểu cảm, confidence 0–1, faces, captured_at, region |
| `/emotion/status` | `std_msgs/msg/String` | JSON action, reason, linear, angular, distance, angle, stopped |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Vận tốc 20 Hz, số 0 khi không được phép chạy |
| `/odom` | `nav_msgs/msg/Odometry` | Vị trí/góc quay để hoàn tất quỹ đạo và giám sát dữ liệu |
| `/emotion/stop` | `std_srvs/srv/Trigger` | Dừng có chốt |
| `/emotion/reset` | `std_srvs/srv/Trigger` | Bỏ chốt; cần Neutral ổn định để nhận lệnh tiếp |

```bash
source ~/ros2_ws/emotion_env.bash
ros2 service call /emotion/stop std_srvs/srv/Trigger '{}'
ros2 service call /emotion/reset std_srvs/srv/Trigger '{}'
ros2 topic echo /emotion/status
```

`captured_at` là `time.monotonic()` của máy webcam. Hai node hiện phải chạy
cùng máy; không phát lại bản tin cũ hay dùng thời gian Unix cho trường này.
Controller dùng đồng hồ steady riêng, nên Gazebo pause không làm ngừng watchdog.
Không có khuôn mặt, nhiều mặt, nhãn Disgust/unknown, điểm số thấp, JSON sai hoặc
kết quả cũ → dừng. Không có kết quả mới trong 1.5 giây hoặc odometry quá 0.6
giây → dừng. Neutral được chấp nhận để dừng kể cả điểm thấp. Độ trễ dừng khi
suy luận treo tối đa khoảng `input_timeout` + một chu kỳ 50 ms, không phải
dừng tức thì theo ảnh chưa phân tích.

Capture/preview và suy luận chạy riêng; chỉ giữ frame mới nhất, không xếp
hàng video cũ. Controller là process riêng nên suy luận bị treo không chặn
việc phát số 0. `enforce_detection=True` đảm bảo ảnh không có mặt không bị
coi là một khuôn mặt. Backend trả 7 lớp; Disgust được giữ nguyên rồi từ chối,
không bị ép sang một trong 6 lệnh. Launch kết thúc khi camera/controller thoát.
Nếu process controller bị SIGKILL hoặc mất máy, cần watchdog `/cmd_vel` của
base robot; node không thể phát số 0 khi đã chết.

## Cấu hình và kiểm thử

Sửa [`config/emotion.yaml`](config/emotion.yaml), hoặc truyền
`config:=/duong/dan/emotion.yaml`. Tốc độ tuyến tính bị giới hạn tối đa 0.20
m/s, góc tối đa 0.8 rad/s. Confidence mặc định 0.65, có thể tăng nếu dễ nhận
nhầm. Khi CPU không kịp, giữ cửa sổ preview mở để xem tuổi ảnh; ảnh quá hạn
không được dùng điều khiển. Không tăng timeout chỉ để che lỗi webcam.

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select turtlebot4_emotion
PYTHONPATH=src/turtlebot4_emotion python3 -m pytest -q src/turtlebot4_emotion/test
```

Kiểm chứng chuyển động trong Gazebo bằng biểu cảm JSON tổng hợp:

```bash
# Terminal 1
./run_emotion_demo.bash camera:=false gazebo_gui:=false
# Terminal 2
source emotion_env.bash
python3 src/turtlebot4_emotion/test/check_gazebo.py
```

Báo cáo được ghi ở `artifacts/emotion/runtime_checks.json`. Đây là kiểm tra
đường điều khiển ROS và odometry, không đo độ chính xác nhận diện biểu cảm.

Nếu không mở được webcam, đóng ứng dụng đang dùng camera, kiểm tra
`ls /dev/video*`, rồi đổi `camera_index`. `/dev/video1` có thể chỉ chứa metadata,
không phải luồng hình. Lỗi tải trọng số: chạy lại setup khi có Internet.
Đứng yên dù thấy biểu cảm: xem `/emotion/status`, kiểm tra `/odom`, điểm số,
độ ổn định và Neutral để cho phép chạy lại.

Tài liệu API: [DeepFace](https://github.com/serengil/deepface),
[DeepFace.analyze](https://github.com/serengil/deepface/blob/master/deepface/DeepFace.py).
Kết quả và phạm vi kiểm chứng tại [VALIDATION.md](VALIDATION.md).
World trống được dẫn xuất từ world của TurtleBot 4 simulator (Apache-2.0),
giữ ghi công trong file SDF.
