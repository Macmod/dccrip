#!/usr/bin/python
from message import Message
from rtable import RoutingTable
from collections import defaultdict as dd
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

# Arg parse
parser = argparse.ArgumentParser(description='DCCRIP Router')
parser.add_argument('addr', metavar='ADDR', type=str,
                    help='Router address.')
parser.add_argument('period', metavar='PERIOD', type=int,
                    help='Send updates every N seconds.')
parser.add_argument('startup', nargs='?', metavar='FILE',
                    help='File to read startup commands from.')

args = parser.parse_args()

UDP_IP = args.addr
UDP_PORT = 55151

try:
    ipaddress.IPv4Address(UDP_IP)
except Exception as e:
    logging.error(str(e))
    sys.exit(1)

# Setup logging
file_handler = logging.FileHandler(filename=LOGPATH + '/' + UDP_IP + '.log')
stdout_handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, stdout_handler],
    format='[%(asctime)s] %(levelname)s: %(message)s',
)

# Routing table
rtable = RoutingTable(UDP_IP)

def send_message(dest, msg):
    global sock, rtable

    cost, gateways = rtable.get_best_gateways(dest)

    if len(gateways) > 0:
        # Load balancing
        gateway = random.choice(gateways)

        # Send
        sock.sendto(str(msg).encode(), (gateway, UDP_PORT))

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
        # Get update messages from routing table
        # and send them to links
        for update in rtable.get_updates():
            sock.sendto(str(update).encode(), (update.destination, UDP_PORT))
    elif cmd == 'routes': # Extra: show topology
        rtable.show_routes()
    elif cmd == 'links': # Extra: show links
        rtable.show_links()
    elif cmd == 'plot': # Extra: plot topology
        rtable.plot(DOTPATH + "/" + UDP_IP)
    else:
        logging.error('Invalid command `' + cmd + '`')

def process_stdin():
    inp = sys.stdin.readline().rstrip()
    handle_command(inp)

def handle_update(ip, msg):
    # Clear routes with this gateway
    rtable.clear(ip)

    # Update routes with this gateway
    rtable.update(ip, msg.distances)

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

def process_message():
    global sock

    data, addr = sock.recvfrom(MAXBUF)
    data = data.decode()

    ip, port = addr
    if ip not in rtable.links:
        logging.warning('Received message from a stranger: ' + ip + '.')
        return
    else:
        logging.info('Got message from ' + ip + '.')

    #  try:
    json_msg = json.loads(data)

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

        try:
            payload_trace = json.loads(json_msg['payload'])
            msg = Message('trace', src, dst, payload_trace)

            logging.info('Trace answered. Hops: ' + ' => '.join(msg.hops))
        except:
            msg = Message('data', src, dst, {'payload': payload})

            if msg.destination == UDP_IP:
                logging.info('Got message for me. Ignoring...')
                return
            else:
                send_message(msg.destination, msg)
    elif mtype == 'update':
        if 'distances' not in json_msg:
            logging.error('Malformed message: no distances field.')
            return
        msg = Message('update', src, dst, {'distances': json_msg['distances']})
        handle_update(ip, msg)
    elif mtype == 'trace':
        if 'hops' not in json_msg:
            logging.error('Malformed message: no hops field.')
            return
        msg = Message('trace', src, dst, {'hops': json_msg['hops']})
        handle_trace(msg)
    #  except:
        #  print('Invalid message received (message is not well-formed json).')
    #  print(data)

if __name__ == '__main__':
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

    while True:
        for key, mask in selector.select():
            callback = key.data
            callback()
