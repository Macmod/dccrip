#!/usr/bin/python
from message import Message
from rtable import RoutingTable
from collections import defaultdict as dd
from threading import Timer, Lock
import selectors
import ipaddress
import argparse
import logging
import random
import socket
import json
import sys

LOGPATH = 'logs'
DOTPATH = 'dot'
MAXBUF = 2**16

def send_message(dest, msg):
    global sock, rtable

    cost, gateways = rtable.get_best_gateways(dest)

    if len(gateways) > 0:
        # Load balancing
        gateway = random.choice(gateways)

        msg_str = str(msg)
        logging.info('Sending message to ' + gateway + ': ' + msg_str)

        # Send
        sock.sendto(msg_str.encode(), (gateway, UDP_PORT))

def broadcast_update():
    global sock, rtable, args, update_timer

    # Get update messages from routing table
    # and send them to links
    for update in rtable.get_updates():
        sock.sendto(str(update).encode(), (update.destination, UDP_PORT))

    update_timer = Timer(args.period, broadcast_update)
    update_timer.start()

def handle_command(inp):
    cmdline = inp.split()
    if len(cmdline) == 0:
        return

    cmd = cmdline[0].lower()

    if cmd == 'add':
        if len(cmdline) < 3:
            logging.error('Wrong command: missing args.')
            return

        ip = cmdline[1]
        weight = int(cmdline[2])

        if not rtable.add_link(ip, weight):
            sys.exit(1)
    elif cmd == 'del':
        if len(cmdline) < 2:
            logging.error('Wrong command: missing args.')
            return

        ip = cmdline[1]
        rtable.del_link(ip)
    elif cmd == 'trace':
        if len(cmdline) < 2:
            logging.error('Wrong command: missing args.')
            return

        trace = Message(cmd, UDP_IP, cmdline[1], {'hops': []})
        send_message(trace.destination, trace)
    elif cmd =='update': # Extra: explicit update command
        broadcast_update()
    elif cmd == 'routes': # Extra: show topology
        rtable.show_routes()
    elif cmd == 'links': # Extra: show links
        rtable.show_links()
    elif cmd == 'plot': # Extra: plot topology
        rtable.plot(DOTPATH + "/" + UDP_IP)
    else:
        logging.error('Invalid command `' + cmd + '`')

def handle_trace(trace):
    trace.hops.append(UDP_IP)

    if trace.destination == UDP_IP:
        # Tunnel answer
        answer = Message('data', trace.destination, trace.source,
                         {'payload': str(trace)})
        send_message(trace.source, answer)
    else:
        # Forward trace
        send_message(trace.destination, trace)

def process_stdin():
    inp = sys.stdin.readline().rstrip()
    handle_command(inp)

def process_message():
    global sock

    data, addr = sock.recvfrom(MAXBUF)
    data = data.decode()

    ip, port = addr
    if ip not in rtable.links:
        logging.warning('Ignoring message from stranger: ' + ip + '.')
        return
    else:
        logging.info('Message from ' + ip + ': ' + data)

    try:
        json_msg = json.loads(data)
    except:
        logging.error('Invalid message received (message is not a valid json).')
        return

    if 'source' not in json_msg or 'destination' not in json_msg or 'type' not in json_msg:
        logging.error('Malformed message.')
        return

    mtype = json_msg['type']
    src = json_msg['source']
    dst = json_msg['destination']

    if mtype == 'data':
        if 'payload' not in json_msg:
            logging.error('Malformed message: no payload found.')
            return

        payload = json_msg['payload']

        msg = Message('data', src, dst, {'payload': payload})

        if msg.destination == UDP_IP:
            try:
                trace = json.loads(json_msg['payload'])
                logging.info('Trace answered. Hops: ' + ' => '.join(trace['hops']))
            except:
                logging.info('Got message for me. Payload: ' + payload)
        else:
            send_message(msg.destination, msg)
    elif mtype == 'update':
        if 'distances' not in json_msg:
            logging.error('Malformed message: no distances field.')
            return
        elif src != ip:
            logging.error(ip + ' tried to spoof the update! Ignoring...')
            return

        rtable.update(ip, json_msg['distances'])
    elif mtype == 'trace':
        if 'hops' not in json_msg:
            logging.error('Malformed message: no hops field.')
            return

        msg = Message('trace', src, dst, {'hops': json_msg['hops']})
        handle_trace(msg)
    else:
        logging.error('Invalid message type `' + mtype + '`.')

if __name__ == '__main__':
    # Arg parse
    parser = argparse.ArgumentParser(description='DCCRIP Router')
    parser.add_argument('addr', metavar='ADDR', type=str,
                        help='Router address.')
    parser.add_argument('period', metavar='PERIOD', type=int,
                        help='Send updates every N seconds.')
    parser.add_argument('startup', nargs='?', metavar='FILE',
                        help='File to read startup commands from.')

    args = parser.parse_args()

    PERIOD = args.period
    UDP_IP = args.addr
    UDP_PORT = 55151

    # Setup logging
    file_handler = logging.FileHandler(filename=LOGPATH + '/' + UDP_IP + '.log')
    stdout_handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, stdout_handler],
        format='[%(asctime)s] %(levelname)s: %(message)s',
    )

    try:
        ipaddress.IPv4Address(UDP_IP)
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)

    if args.period <= 0:
        logging.error('`' + str(args.period) + '` is not a valid update period.')
        sys.exit(1)

    # Routing table
    rtable = RoutingTable(UDP_IP, PERIOD)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    logging.info('Binding to ' + UDP_IP + ':' + str(UDP_PORT))

    if args.startup:
        logging.info('Running startup commands...')

        startup = open(args.startup, 'r')
        for line in startup:
            handle_command(line.rstrip())

    selector = selectors.DefaultSelector()
    selector.register(sys.stdin, selectors.EVENT_READ, process_stdin)
    selector.register(sock, selectors.EVENT_READ, process_message)

    update_timer = Timer(args.period, broadcast_update)
    update_timer.start()

    while True:
        for key, mask in selector.select():
            callback = key.data
            callback()
