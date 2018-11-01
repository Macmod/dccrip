#!/bin/sh
set -eu

exe="./router.py"
startup="scripts/tree"
updatetime=$1

tmux new-session -x 2000 -y 2000 -d -s tree "$exe --addr 127.0.1.1 --update-period $updatetime --startup-commands $startup/1.txt" &&
tmux select-layout -t tree tiled

tmux rename-window -t tree "Tree Topology"

for i in $(seq 2 6); do
    tmux split-window -t tree -v "$exe --addr 127.0.1.$i --update-period $updatetime --startup-commands $startup/$i.txt" &&
    tmux select-layout -t tree tiled
done

tmux -2 attach -t tree
