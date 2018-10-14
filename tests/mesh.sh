#!/bin/sh

tmux new-session -x 2000 -y 2000 -d -s sample './router.py 127.0.0.1 1 tests/mesh/1.txt'
tmux rename-window 'Mesh Topology'

tmux split-window -v "./router.py 127.0.0.2 1 tests/mesh/2.txt"
tmux split-window -v "./router.py 127.0.0.3 1 tests/mesh/3.txt"

tmux split-window -v "./router.py 127.0.0.4 1 tests/mesh/4.txt"
tmux split-window -v "./router.py 127.0.0.5 1 tests/mesh/5.txt"
tmux split-window -v "./router.py 127.0.0.6 1 tests/mesh/6.txt"

tmux split-window -v "./router.py 127.0.0.7 1 tests/mesh/7.txt"
tmux split-window -v "./router.py 127.0.0.8 1 tests/mesh/8.txt"
tmux split-window -v "./router.py 127.0.0.9 1 tests/mesh/9.txt"

tmux select-layout tiled
# tmux send-keys -t 4 'update' 'C-m'

sleep 2

for i in {0..8}; do
    tmux send-keys -t $i 'plot' 'C-m'
done

tmux -2 attach-session -t sample
