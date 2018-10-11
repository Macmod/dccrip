#!/bin/sh
set -eu

# exe="python3.5 ../../router.pyc"
exe="../../router.py"

for i in $(seq 1 6) ; do
    echo "$exe 127.0.0.$i 30 $i.txt"
    tmux split-pane -v "$exe 127.0.1.$i 30 $i.txt" &
    tmux select-layout even-vertical
done
