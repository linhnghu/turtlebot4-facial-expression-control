from glob import glob
from setuptools import find_packages, setup

setup(
    name='turtlebot4_emotion', version='0.1.0', packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/turtlebot4_emotion']),
        ('share/turtlebot4_emotion', ['package.xml', 'README.md', 'VALIDATION.md', 'requirements.txt']),
        ('share/turtlebot4_emotion/launch', glob('launch/*.launch.py')),
        ('share/turtlebot4_emotion/config', glob('config/*.yaml')),
        ('share/turtlebot4_emotion/worlds', glob('worlds/*.sdf')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Linh', maintainer_email='linh@example.com', license='Apache-2.0',
    description='Webcam facial expression recognition and bounded TurtleBot motion',
    entry_points={'console_scripts': [
        'emotion_controller = turtlebot4_emotion.controller:main',
        'emotion_camera = turtlebot4_emotion.camera:main',
    ]},
)
