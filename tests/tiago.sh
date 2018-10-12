#!/bin/sh

# Setup window
tmux new-session -d -s sample './router.py 127.0.0.2 1'

tmux select-window -t sample:0
tmux rename-window 'Star Topology'

tmux split-window -h './router.py 127.0.0.1 1'

tmux split-window -v -t 0 './router.py 127.0.0.4 1'

tmux split-window -v -t 1 './router.py 127.0.0.5 1'

tmux split-window -v -t 0 './router.py 127.0.0.3 1'

# Send commands
tmux send-keys -t 0 'add 127.0.0.3 10' 'C-m'
tmux send-keys -t 0 'add 127.0.0.4 4' 'C-m'
tmux send-keys -t 1 'add 127.0.0.5 9' 'C-m'
tmux send-keys -t 2 'add 127.0.0.5 5' 'C-m'

tmux send-keys -t 4 'add 127.0.0.2 1' 'C-m'

# tmux send-keys -t 4 'update' 'C-m'

sleep 2

for i in {0..4}; do
    tmux send-keys -t $i 'plot' 'C-m'
done

tmux -2 attach-session -t sample

