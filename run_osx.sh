#!/bin/bash

# Get the current directory
current_dir=$(pwd)

# Open the first terminal window and execute commands
osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$current_dir' && redis-server"
end tell
EOF

# Open the second terminal window and execute commands
osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$current_dir' && conda activate chat-tasks && python worker.py"
end tell
EOF

# Open the third terminal window and execute commands
osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$current_dir' && conda activate chat-tasks && flask run"
end tell
EOF
