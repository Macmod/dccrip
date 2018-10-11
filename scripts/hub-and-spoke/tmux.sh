#!/bin/sh
set -eu

# exe="python3.5 ../../router.pyc"
exe="../../router.py"

echo "$exe 127.0.1.10 1 hub.txt"
tmux split-pane -v $exe 127.0.1.10 1 hub.txt &

for i in $(seq 1 5) ; do
    tmux split-pane -v $exe "127.0.1.$i" 1 spoke.txt &
    tmux select-layout even-vertical
done
