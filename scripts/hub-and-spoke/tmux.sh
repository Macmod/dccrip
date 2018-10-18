#!/bin/sh
set -eu

exe="./router.py"
startup="scripts/hub-and-spoke"

tmux split-pane -v $exe --addr 127.0.1.10 --update-period 1 --startup-commands $startup/hub.txt &

for i in $(seq 1 5) ; do
    tmux split-pane -v $exe --addr "127.0.1.$i" --update-period 1 --startup-commands $startup/spoke.txt &
    tmux select-layout even-vertical
done
