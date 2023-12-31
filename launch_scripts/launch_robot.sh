#!/bin/bash

# Automated running all hardware nodes
# use bash command to make a file  ~/.tmux.conf and add lines to print pane name
# if [ ! -f ~/.tmux.conf ]; then
# add lines to tmux config to print pane name
# touch ~/.tmux.conf
# echo "set-option -g pane-border-status top" >> ~/.tmux.conf
# echo "set -g pane-border-format '[#[fg=white]#{?pane_active,#[bold],} #P #T #[fg=default,nobold]]'" >> ~/.tmux.conf


SESSION_NAME="Alfred Autonomy Stack!"
if tmux has-session -t "$SESSION_NAME" >/dev/null 2>&1; then
    # If session exists, attach to it
    tmux attach-session -t "$SESSION_NAME"
    tmux source-file ~/alfred-autonomy/confs/.tmux-conf
else
    # Launch tmux session
    rosnode kill --all
    tmux new-session -d -s autonomy
    tmux source-file ~/alfred-autonomy/confs/.tmux-conf
    #split window into 3x3 grid
    tmux split-window -v
    tmux split-window -v
    tmux split-window -v
    tmux select-pane -t 0
    tmux split-window -h
    tmux select-pane -t 2
    tmux split-window -h
    tmux select-pane -t 4
    tmux split-window -h
    tmux select-pane -t 6
    tmux split-window -h
        
    # Run commands in each pane (add sleeps to wait for roscore to start)
    tmux send-keys -t 0 "sleep 1 && roslaunch alfred_core driver.launch " C-m
    tmux send-keys -t 1 "sleep 5 && roslaunch alfred_core perception_robot_tuned.launch" C-m
    tmux send-keys -t 2 "sleep 5 && roslaunch alfred_navigation navigation_no_driver.launch" C-m
    tmux send-keys -t 3 "sleep 5 && roslaunch task_planner task_planner.launch" C-m
    tmux send-keys -t 4 "sleep 5 && roslaunch manipulation robot_manipulation.launch" C-m
    tmux send-keys -t 5 "sleep 5 && roslaunch alfred_hri hri.launch" C-m
    tmux send-keys -t 6 "sleep 5 && ssh praveen@alfredbrain 'bash -s < /home/praveen/alfred-autonomy/launch_scripts/launch_brain.sh'" C-m
    # tmux send-keys -t 7 "sleep 5 && ssh abhinav@alfredbrain 'bash -s < /home/abhinav/FVD/alfred-autonomy/launch_scripts/launch_brain_vlmaps.sh'" C-m
    

    # Attach to tmux session
    tmux attach-session -t autonomy
fi