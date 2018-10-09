#!/bin/sh

# Setup window
tmux new-session -d -s sample './router.py 127.0.0.2 3'

tmux select-window -t sample:0
tmux rename-window 'Star Topology'

tmux split-window -h './router.py 127.0.0.1 3'

tmux split-window -v -t 0 './router.py 127.0.0.3 3'

tmux split-window -v -t 1 './router.py 127.0.0.4 3'

tmux split-window -v -t 0 './router.py 127.0.0.5 3'

# Send commands
tmux send-keys -t 0 'add 127.0.0.1 10' 'C-m'
tmux send-keys -t 1 'add 127.0.0.1 10' 'C-m'
tmux send-keys -t 2 'add 127.0.0.1 10' 'C-m'
tmux send-keys -t 3 'add 127.0.0.1 10' 'C-m'

tmux send-keys -t 4 'add 127.0.0.2 6' 'C-m'
tmux send-keys -t 4 'add 127.0.0.3 9' 'C-m'
tmux send-keys -t 4 'add 127.0.0.4 12' 'C-m'
tmux send-keys -t 4 'add 127.0.0.5 15' 'C-m'

sleep 1

tmux send-keys -t 4 'update' 'C-m'

sleep 1

for i in {0..4}; do
    tmux send-keys -t $i 'plot' 'C-m'
done

tmux -2 attach-session -t sample

