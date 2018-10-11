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

class Router():
    def __init__(self, ip, port, removal_time, update_time, maxbuf=2**16,
                 logpath='logs', dotpath='dot', startupfile=None):
        self.ip = ip
        self.port = port
        self.removal_time = removal_time
        self.update_time = update_time
        self.maxbuf = maxbuf
        self.logpath = logpath
        self.dotpath = dotpath
        self.rtable = RoutingTable(ip, removal_time)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))

        # Setup logging
        file_handler = logging.FileHandler(filename=self.logpath + '/' + self.ip + '.log')
        stdout_handler = logging.StreamHandler(sys.stdout)
        logging.basicConfig(
            level=logging.DEBUG,
            handlers=[stdout_handler, file_handler],
            format='[%(asctime)s] %(levelname)s: %(message)s',
        )

        logging.info('Binding to ' + ip + ':' + str(port))

        self.selector = selectors.DefaultSelector()
        self.selector.register(sys.stdin, selectors.EVENT_READ, self.process_stdin)
        self.selector.register(self.sock, selectors.EVENT_READ, self.process_udp)

        self.lock = Lock()

        if startupfile:
            logging.info('Running startup commands...')

            startup = open(startupfile, 'r')
            for line in startup:
                self.handle_command(line.rstrip())

    def start(self):
        self.update_timer = Timer(self.update_time, self.broadcast_update)
        self.update_timer.start()

        while True:
            for key, mask in self.selector.select():
                callback = key.data
                callback()

    def send_message(self, dest, msg):
        cost, gateways = self.rtable.get_best_gateways(dest)

        if len(gateways) > 0:
            # Load balancing
            gateway = random.choice(gateways)

            msg_str = str(msg)
            logging.info('Sending message to ' + gateway + ': ' + msg_str)

            # Send
            self.sock.sendto(msg_str.encode(), (gateway, self.port))

    def broadcast_update(self):
        self.lock.acquire()

        # Get update messages from routing table
        # and send them to links
        for update in self.rtable.get_updates():
            self.sock.sendto(str(update).encode(), (update.destination, self.port))

        self.update_timer = Timer(self.update_time, self.broadcast_update)
        self.update_timer.start()

        self.lock.release()

    def handle_command(self, inp):
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

            if not self.rtable.add_link(ip, weight):
                sys.exit(1)
        elif cmd == 'del':
            if len(cmdline) < 2:
                logging.error('Wrong command: missing args.')
                return

            ip = cmdline[1]
            self.rtable.del_link(ip)
        elif cmd == 'trace':
            if len(cmdline) < 2:
                logging.error('Wrong command: missing args.')
                return

            trace = Message(cmd, UDP_IP, cmdline[1], {'hops': []})
            self.send_message(trace.destination, trace)
        elif cmd =='update': # Extra: explicit update command
            broadcast_update()
        elif cmd == 'routes': # Extra: show topology
            self.rtable.show_routes()
        elif cmd == 'links': # Extra: show links
            self.rtable.show_links()
        elif cmd == 'plot': # Extra: plot topology
            self.rtable.plot(self.dotpath + "/" + self.ip)
        else:
            logging.error('Invalid command `' + cmd + '`')

    def handle_trace(self, trace):
        trace.hops.append(self.ip)

        if trace.destination == self.ip:
            # Tunnel answer
            answer = Message('data', trace.destination, trace.source,
                             {'payload': str(trace)})
            self.send_message(trace.source, answer)
        else:
            # Forward trace
            self.send_message(trace.destination, trace)

    def handle_message(self, data, addr):
        ip, port = addr
        if ip not in self.rtable.links:
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

            if msg.destination == self.ip:
                try:
                    trace = json.loads(json_msg['payload'])
                    logging.info('Trace answered. Hops: ' + ' => '.join(trace['hops']))
                except:
                    logging.info('Got message for me. Payload: ' + payload)
            else:
                self.send_message(msg.destination, msg)
        elif mtype == 'update':
            if 'distances' not in json_msg:
                logging.error('Malformed message: no distances field.')
                return
            elif src != ip:
                # Extra: anti-spoofing of update messages
                logging.error(ip + ' tried to spoof the update! Ignoring...')
                return

            self.rtable.update(ip, json_msg['distances'])
        elif mtype == 'trace':
            if 'hops' not in json_msg:
                logging.error('Malformed message: no hops field.')
                return

            msg = Message('trace', src, dst, {'hops': json_msg['hops']})
            self.handle_trace(msg)
        else:
            logging.error('Invalid message type `' + mtype + '`.')

    def process_stdin(self):
        inp = sys.stdin.readline().rstrip()

        self.lock.acquire()
        self.handle_command(inp)
        self.lock.release()

    def process_udp(self):
        data, addr = self.sock.recvfrom(self.maxbuf)
        data = data.decode()

        self.lock.acquire()
        self.handle_message(data, addr)
        self.lock.release()

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

    UPDATE_TIME = args.period
    UDP_IP = args.addr
    UDP_PORT = 55151

    # Validate parameters
    try:
        ipaddress.IPv4Address(UDP_IP)
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)

    if args.period <= 0:
        logging.error('`' + str(args.period) + '` is not a valid update period.')
        sys.exit(1)

    # Start router
    router = Router(UDP_IP, UDP_PORT, UPDATE_TIME, 4*UPDATE_TIME)
    router.start()
