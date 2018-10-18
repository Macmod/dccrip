#!/bin/sh
set -eu

exe="./router.py"
startup="scripts/fish-ecmp"

for i in $(seq 1 6) ; do
    tmux split-pane -v $exe --addr 127.0.1.$i --update-period 180 --startup-commands $startup/$i.txt &
    tmux select-layout even-vertical
done
