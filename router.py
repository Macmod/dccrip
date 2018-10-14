#!/usr/bin/python
from message import Message
from rtable import RoutingTable
from collections import defaultdict as dd
from threading import Timer, Lock
import selectors
import ipaddress
import datetime
import argparse
import logging
import random
import socket
import json
import time
import sys

class Router():
    def __init__(self, ip, port, update_time, removal_time, maxbuf=2**16,
                 logpath='logs', dotpath='dot', startupfile=None):
        self.ip = ip
        self.port = port
        self.removal_time = removal_time
        self.update_time = update_time
        self.last_update = time.time()
        self.maxbuf = maxbuf
        self.logpath = logpath
        self.dotpath = dotpath
        self.lock = Lock()
        self.rtable = RoutingTable(ip, removal_time, self.lock)

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

        if startupfile:
            logging.info('Running startup commands...')

            startup = open(startupfile, 'r')
            for line in startup:
                self.handle_command(line.rstrip())

    def start(self):
        self.update_timer = Timer(self.update_time, self.__broadcast_update_callback)
        self.update_timer.start()

        while True:
            for key, mask in self.selector.select():
                callback = key.data
                callback()

    def send_message(self, msg):
        cost, gateways = self.rtable.get_best_gateways(msg.destination)

        if len(gateways) == 0:
            if msg.source != self.ip and msg.type in ('data', 'trace'):
                noroute = Message('data', self.ip, msg.source, {
                    'payload': 'Hop ' + self.ip + ' has no route to ' + msg.destination + '.'
                })

                self.send_message(noroute)

            return False

        # Load balancing
        gateway = random.choice(gateways)

        msg_str = str(msg)
        logging.info('Sending message to ' + msg.destination + ' via ' + gateway + ': ' + msg_str)

        # Send
        self.sock.sendto(msg_str.encode(), (gateway, self.port))

        return True

    def __broadcast_update_callback(self):
        self.lock.acquire()

        self.broadcast_update()

        self.update_timer = Timer(self.update_time, self.__broadcast_update_callback)
        self.update_timer.start()

        self.last_update = time.time()

        self.lock.release()

    def broadcast_update(self):
        # Get update messages from routing table
        # and send them to links
        for update in self.rtable.get_updates():
            self.sock.sendto(str(update).encode(), (update.destination, self.port))

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
            self.send_message(trace)
        elif cmd =='update': # Extra: explicit update command
            self.broadcast_update()
        elif cmd == 'routes': # Extra: show topology
            self.rtable.show_routes()
        elif cmd == 'links': # Extra: show links
            self.rtable.show_links()
        elif cmd == 'time': # Extra: show time until next update
            delta = self.update_time - (time.time() - self.last_update)
            print("{:0>8} until update".format(str(datetime.timedelta(seconds=delta))))
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
            self.send_message(answer)
        else:
            # Forward trace
            self.send_message(trace)

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
                logging.info('Data from ' + msg.source + ': ' + payload)

                try:
                    trace = json.loads(json_msg['payload'])
                    logging.info('Trace answered. Hops: ' + ' => '.join(trace['hops']))
                except:
                    pass
            else:
                self.send_message(msg)
        elif mtype == 'update':
            if 'distances' not in json_msg:
                logging.error('Malformed message: no distances field.')
                return
            elif src != ip:
                # Extra: anti-spoofing of update messages
                logging.error(ip + ' tried to spoof the update! Ignoring...')
                return

            self.rtable.update_routes(ip, json_msg['distances'])
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
    parser.add_argument('ADDR', metavar='ADDR', type=str,
                        help='Router address.')
    parser.add_argument('PERIOD', metavar='PERIOD', type=int,
                        help='Send updates every N seconds.')
    parser.add_argument('STARTUP', nargs='?', metavar='FILE',
                        help='File to read startup commands from.')

    args = parser.parse_args()

    UPDATE_TIME = args.PERIOD
    UDP_IP = args.ADDR
    STARTUP = args.STARTUP
    UDP_PORT = 55151

    # Validate parameters
    try:
        ipaddress.IPv4Address(UDP_IP)
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)

    if UPDATE_TIME <= 0:
        logging.error('`' + str(UPDATE_TIME) + '` is not a valid update period.')
        sys.exit(1)

    # Start router
    router = Router(UDP_IP, UDP_PORT, UPDATE_TIME, 4*UPDATE_TIME, startupfile=STARTUP)
    router.start()
