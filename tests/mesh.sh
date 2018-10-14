#!/bin/sh

# Setup window
tmux new-session -d -s sample 'python3.5 ./router.py 127.0.0.1 1 tests/mesh/1.txt'

tmux select-window -t sample:0
tmux rename-window 'Mesh Topology'

tmux split-window -h -t 0 "python3.5 ./router.py 127.0.0.2 1 tests/mesh/2.txt"

tmux split-window -h -t 1 "python3.5 ./router.py 127.0.0.3 1 tests/mesh/3.txt"

tmux split-window -v -t 0 "python3.5 ./router.py 127.0.0.4 1 tests/mesh/4.txt"
tmux split-window -v -t 1 "python3.5 ./router.py 127.0.0.5 1 tests/mesh/5.txt"
tmux split-window -v -t 2 "python3.5 ./router.py 127.0.0.6 1 tests/mesh/6.txt"

tmux split-window -v -t 3 "python3.5 ./router.py 127.0.0.7 1 tests/mesh/7.txt"
tmux split-window -v -t 4 "python3.5 ./router.py 127.0.0.8 1 tests/mesh/8.txt"
tmux split-window -v -t 5 "python3.5 ./router.py 127.0.0.9 1 tests/mesh/9.txt"

# tmux send-keys -t 4 'update' 'C-m'

sleep 2

for i in {0..8}; do
    tmux send-keys -t $i 'plot' 'C-m'
done

tmux -2 attach-session -t sample

