#!/bin/sh
set -eu

exe="./router.py"
startup="scripts/fish-ecmp"
updatetime=$1

tmux new-session -x 2000 -y 2000 -d -s fishecmp "$exe --addr 127.0.1.1 --update-period $updatetime --startup-commands $startup/1.txt" &&
tmux select-layout -t fishecmp even-vertical

tmux rename-window -t fishecmp 'Fish ECMP Topology'

for i in $(seq 2 6) ; do
    tmux split-pane -t fishecmp -v "$exe --addr 127.0.1.$i --update-period $updatetime --startup-commands $startup/$i.txt" &&
    tmux select-layout -t fishecmp even-vertical
done

tmux -2 attach -t fishecmp
