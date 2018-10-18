#!/bin/sh

exe='./router.py'
startup='scripts/mesh'

# Setup window
tmux new-session -x 2000 -y 2000 -d -s sample "$exe --addr 127.0.0.1 --update-period 6 --startup-commands $startup/1.txt"
tmux rename-window 'Mesh Topology'

for i in $(seq 2 9); do
    tmux split-window -v "$exe --addr 127.0.0.$i --update-period 6 --startup-commands $startup/$i.txt"
done

tmux select-layout tiled

sleep 3

# Plot topology
for i in {0..8}; do
    tmux send-keys -t $i 'plot' 'C-m'
done

# Attach
tmux -2 attach-session -t sample
