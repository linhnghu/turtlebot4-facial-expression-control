# Source this file in every terminal used with the facial expression demo.
_emotion_ws="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${_emotion_ws}/turtlebot4_env.bash"
export EMOTION_WORKSPACE="${_emotion_ws}"
export ROS_DOMAIN_ID="${EMOTION_DOMAIN_ID:-69}"
export ROS_LOCALHOST_ONLY="${EMOTION_LOCALHOST_ONLY:-1}"
export IGN_PARTITION="${EMOTION_IGN_PARTITION:-emotion_${USER}_${ROS_DOMAIN_ID}}"
export DEEPFACE_HOME="${_emotion_ws}/.models/emotion"
unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GIO_MODULE_DIR GIO_EXTRA_MODULES
unset GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR QT_QPA_PLATFORM_PLUGIN_PATH GSETTINGS_SCHEMA_DIR
if [[ -n "${XDG_DATA_DIRS_VSCODE_SNAP_ORIG:-}" ]]; then
    export XDG_DATA_DIRS="$XDG_DATA_DIRS_VSCODE_SNAP_ORIG"
fi
unset _emotion_ws
