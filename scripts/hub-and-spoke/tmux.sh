#!/bin/sh
set -eu

exe="./router.py"
startup="scripts/hub-and-spoke"
updatetime=$1

tmux new-session -x 2000 -y 2000 -d -s hubspoke "$exe --addr 127.0.1.10 --update-period $updatetime --startup-commands $startup/hub.txt" &&
tmux select-layout -t hubspoke even-vertical

tmux rename-window -t hubspoke "Hub & Spoke Topology"

for i in $(seq 1 5); do
    tmux split-pane -t hubspoke -v "$exe --addr 127.0.1.$i --update-period $updatetime --startup-commands $startup/spoke.txt" &&
    tmux select-layout -t hubspoke even-vertical
done

tmux -2 attach -t hubspoke
