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
else
    # Launch tmux session
    rosnode kill --all
    tmux new-session -d -s autonomy

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
    # tmux send-keys -t 0 "roscore" C-m
    tmux send-keys -t 0 "roslaunch alfred_core driver.launch " C-m
    tmux send-keys -t 2 "sleep 3 && roslaunch alfred_navigation navigation_no_driver.launch" C-m
    tmux send-keys -t 3 "sleep 5 && rosrun task_planner task_planner.py" C-m
    tmux send-keys -t 7 "htop" C-m

    # Attach to tmux session
    tmux attach-session -t autonomy
fi