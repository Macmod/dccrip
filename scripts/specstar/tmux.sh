#!/bin/sh

exe='./router.py'
startup='scripts/specstar'

# Setup window
tmux new-session -d -s sample "$exe --addr 127.0.0.2 --update-period 1 --startup-commands $startup/2.txt"
tmux rename-window 'Star Topology'

tmux split-window -h "$exe --addr 127.0.0.1 --update-period 1 --startup-commands $startup/1.txt"

tmux split-window -v -t 0 "$exe --addr 127.0.0.4 --update-period 1 --startup-commands $startup/4.txt"

tmux split-window -v -t 1 "$exe --addr 127.0.0.5 --update-period 1 --startup-commands $startup/5.txt"

tmux split-window -v -t 0 "$exe --addr 127.0.0.3 --update-period 1 --startup-commands $startup/3.txt"

sleep 3

# Plot topology
for i in {0..4}; do
    tmux send-keys -t $i 'plot' 'C-m'
done

# Attach
tmux -2 attach-session -t sample
