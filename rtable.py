from collections import defaultdict as dd
from threading import Timer
from message import Message
from utils import IPv4
try:
    from graphviz import *
    GRAPHVIZ = True
except ImportError:
    print('[x] Please install graphviz for topology plot support.')
    GRAPHVIZ = False

import logging

class RoutingTable:
    def __init__(self, ip, removal_time, lock):
        self.routes = dd(lambda: dd(lambda: -1))
        self.links = dd(lambda: -1)
        self.timers = dd(lambda: -1)

        self.ip = ip
        self.removal_time = removal_time
        self.lock = lock

        if GRAPHVIZ:
            self.dot = Digraph()
        else:
            self.dot = None

    def add_link(self, ip, weight):
        if not IPv4(ip):
            logging.error('Invalid IP!')
            return False
        elif ip == self.ip:
            logging.error('Cannot add self link!')
            return False
        elif ip in self.links:
            logging.error('Link already exists!')
            return False
        elif weight < 0:
            logging.error('Weight must be non-negative!')
            return False

        self.links[ip] = weight

        self.timers[ip] = Timer(self.removal_time, self.__del_routes_closure(ip))
        self.timers[ip].start()

        return True

    def add_route(self, dest, via, cost):
        if dest == self.ip or dest == via or via not in self.links:
            return False

        route_cost = self.links[via] + cost
        self.routes[dest][via] = route_cost

        return True

    def del_link(self, ip):
        if not IPv4(ip):
            logging.error('Invalid IP!')
            return False

        if ip in self.links:
            del self.links[ip]

            self.timers[ip].cancel()
            del self.timers[ip]

        self.del_routes_via(ip)
        return True

    def del_route(self, dest, via):
        if dest in self.routes and via in self.routes[dest]:
            del self.routes[dest][via]

            if not self.routes[dest]:
                del self.routes[dest]

    def del_routes_via(self, via):
        dests = list(self.routes.keys())
        for dest in dests:
            self.del_route(dest, via)

    def __del_routes_closure(self, ip):
        def destroyer():
            self.lock.acquire()
            self.del_routes_via(ip)
            self.lock.release()

        return destroyer

    def update_routes(self, via, distances):
        self.timers[via].cancel()

        self.timers[via] = Timer(self.removal_time, self.__del_routes_closure(via))
        self.timers[via].start()

        for dest in distances:
            self.add_route(dest, via, distances[dest])

        dests = list(self.routes.keys())
        for dest in dests:
            if via in self.routes[dest]:
                # For each of my routes using this gateway, if the destination
                # is not mentioned in distances, the route disappeared.
                if dest not in distances:
                    self.del_route(dest, via)

    def get_best_gateways(self, dest):
        mincost = -1
        gateways = []

        if dest in self.routes:
            routes = self.routes[dest].items()
            costs = [cost for via, cost in routes if cost != -1]

            if len(costs) > 0:
                mincost = min(costs)
                gateways = [via for via, cost in routes if cost == mincost]

        if dest in self.links:
            if mincost == -1 or self.links[dest] < mincost:
                mincost = self.links[dest]
                gateways = [dest]
            elif self.links[dest] == mincost:
                gateways.append(dest)

        if mincost != -1:
            logging.info('Found ' + str(len(gateways)) + ' gateways to ' + dest + ' with cost ' + str(mincost) + ': ' + ', '.join(gateways) + '.')
        else:
            logging.warning('No route to ' + dest + '.')

        return mincost, gateways

    def get_all_best_gateways(self, ignore=None):
        distances = {}

        known_dests = self.routes.keys() | self.links.keys()
        for dest in known_dests:
            mincost, gateways = self.get_best_gateways(dest)

            # Split horizon
            if ignore:
                if ignore in gateways:
                    gateways.remove(ignore)
                if dest == ignore:
                    continue

            if len(gateways) > 0:
                distances[dest] = mincost

        return distances

    def get_updates(self):
        for link in self.links:
            # Get distances applying split horizon
            all_best_gateways = self.get_all_best_gateways(ignore=link)

            # Create update message
            msg = Message('update', self.ip, link, {'distances': all_best_gateways})

            # Yield update to caller
            yield msg

    def plot(self, path):
        if not self.dot:
            return False

        self.dot.clear()
        self.dot.node('root', label=self.ip, style='filled',
                      color='lightgrey')

        for link in self.links:
            self.dot.node(link, label=link)
            self.dot.edge('root', link, label=str(self.links[link]))

        for dest in self.routes:
            for via in self.routes[dest]:
                total_cost = self.routes[dest][via] - self.links[via]
                self.dot.edge(
                    via, dest, label=str(total_cost), style='dashed'
                )

        self.dot.render(path)
        return True

    def show_links(self):
        print('\nADDRESS\tWEIGHT')
        for dest in self.links:
            print(dest + '\t' + str(self.links[dest]))
        print()

    def show_routes(self):
        print(self)

    def __str__(self):
        tbl = '\nDESTINATION\tGATEWAY IP\tCOST\n'
        for dest in self.routes:
            for via in self.routes[dest]:
                cost = self.routes[dest][via]
                tbl += dest + '\t' + via + '\t' + str(cost) + '\n'

        return tbl
