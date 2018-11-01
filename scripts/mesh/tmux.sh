#!/bin/sh
set -eu

exe="./router.py"
startup="scripts/mesh"
updatetime=$1

tmux new-session -x 2000 -y 2000 -d -s mesh "$exe --addr 127.0.1.1 --update-period $updatetime --startup-commands $startup/1.txt" &&
tmux select-layout -t mesh tiled

tmux rename-window -t mesh 'Mesh Topology'

for i in $(seq 2 9); do
    tmux split-window -t mesh -v "$exe --addr 127.0.1.$i --update-period $updatetime --startup-commands $startup/$i.txt" &&
    tmux select-layout -t mesh tiled
done

tmux -2 attach -t mesh
