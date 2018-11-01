#!/bin/sh
set -eu

exe="./router.py"
startup="scripts/fish-asymmetric"
updatetime=$1

tmux new-session -x 2000 -y 2000 -d -s fishasym "$exe --addr 127.0.1.1 --update-period $updatetime --startup-commands $startup/1.txt" &&
tmux select-layout -t fishasym even-vertical

tmux rename-window -t fishasym "Fish Asymmetric Topology"

for i in $(seq 2 6) ; do
    tmux split-pane -t fishasym -v "$exe --addr 127.0.1.$i --update-period $updatetime --startup-commands $startup/$i.txt" &&
    tmux select-layout -t fishasym even-vertical
done

tmux -2 attach -t fishasym
