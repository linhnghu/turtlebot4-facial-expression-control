"""One launch for the real webcam, emotion controller and optional TurtleBot simulation."""
import os
from pathlib import Path
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, ExecuteProcess,
                            IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    value = lambda name: LaunchConfiguration(name).perform(context)
    share = Path(get_package_share_directory('turtlebot4_emotion'))
    config = yaml.safe_load(Path(value('config')).expanduser().read_text())
    input_timeout = config['emotion_controller']['ros__parameters'].get('input_timeout', 1.5)
    actions = []
    if value('simulation') == 'true':
        actions.append(IncludeLaunchDescription(PythonLaunchDescriptionSource(
            str(share/'launch/simulation.launch.py')), launch_arguments={'gui': value('gazebo_gui')}.items()))
    controller = Node(package='turtlebot4_emotion', executable='emotion_controller',
        parameters=[value('config')], remappings=[('/cmd_vel', value('cmd_vel_topic')),
                                                ('/odom', value('odom_topic'))], output='screen')
    critical = [controller]
    if value('camera') == 'true':
        python = Path(value('camera_python')).expanduser()
        if not python.is_file():
            raise RuntimeError('Run ./setup_emotion.bash first')
        camera = ExecuteProcess(cmd=[str(python), '-c',
            'from turtlebot4_emotion.camera import main; main()', '--ros-args',
            '-p', 'camera_index:='+value('camera_index'),
            '-p', 'input_timeout:='+str(float(input_timeout)),
            '-p', 'show_window:='+value('show_window')], output='screen',
            additional_env={'CUDA_VISIBLE_DEVICES': '-1', 'TF_CPP_MIN_LOG_LEVEL': '2',
                'TF_NUM_INTRAOP_THREADS': '2', 'TF_NUM_INTEROP_THREADS': '1',
                'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '1'})
        critical.append(camera)
    for process in critical:
        actions.append(RegisterEventHandler(OnProcessExit(target_action=process,
            on_exit=[EmitEvent(event=Shutdown(reason='Emotion process exited'))])))
    actions.extend(critical)
    return actions


def generate_launch_description():
    workspace = Path(os.environ.get('EMOTION_WORKSPACE', str(Path.home()/'ros2_ws')))
    share = Path(get_package_share_directory('turtlebot4_emotion'))
    return LaunchDescription([
        DeclareLaunchArgument('simulation', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('gazebo_gui', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('camera', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('show_window', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('camera_index', default_value='0'),
        DeclareLaunchArgument('camera_python', default_value=str(workspace/'.venv-emotion/bin/python')),
        DeclareLaunchArgument('config', default_value=str(share/'config/emotion.yaml')),
        DeclareLaunchArgument('cmd_vel_topic', default_value='/cmd_vel'),
        DeclareLaunchArgument('odom_topic', default_value='/odom'),
        OpaqueFunction(function=setup),
    ])
