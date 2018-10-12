#!/bin/sh

# Setup window
tmux new-session -d -s sample './router.py 127.0.0.2 1 tests/specstar/2.txt'

tmux select-window -t sample:0
tmux rename-window 'Star Topology'

tmux split-window -h './router.py 127.0.0.1 1 tests/specstar/1.txt'

tmux split-window -v -t 0 './router.py 127.0.0.4 1 tests/specstar/4.txt'

tmux split-window -v -t 1 './router.py 127.0.0.5 1 tests/specstar/5.txt'

tmux split-window -v -t 0 './router.py 127.0.0.3 1 tests/specstar/3.txt'

# tmux send-keys -t 4 'update' 'C-m'

sleep 2

for i in {0..4}; do
    tmux send-keys -t $i 'plot' 'C-m'
done

tmux -2 attach-session -t sample

