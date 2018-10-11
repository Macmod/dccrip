#! /usr/bin/env python
from collections import defaultdict as dd
from threading import Timer
from graphviz import *
from message import *
import logging

class RoutingTable:
    def __init__(self, ip, timeout):
        self.routes = dd(lambda: dd(lambda: -1))
        self.links = dd(lambda: -1)
        #  self.timers = dd(lambda: -1)
        self.timeout = timeout
        self.ip = ip

        self.dot = Digraph()
        self.dot.node('root', label=self.ip, style='filled', color='lightgrey')

    def add_link(self, ip, weight):
        if ip == self.ip:
            logging.error('Cannot add self link!')
            return False
        elif ip in self.links:
            logging.error('Link already exists!')
            return False
        elif weight < 0:
            logging.error('Weight must be non-negative!')
            return False

        self.links[ip] = weight

        #  self.timers[ip] = Timer(self.timeout, lambda: self.del_link(ip))
        #  self.timers[ip].start()

        return True

    def del_link(self, ip):
        if ip in self.links:
            del self.links[ip]
            #  del self.timers[ip]

        for dest in self.routes:
            if ip in self.routes[dest]:
                del self.routes[dest][ip]

    def update(self, via, distances):
        for dest in distances:
            self.add_route(dest, via, distances[dest])

        for dest in self.routes:
            if via in self.routes[dest]:
                # For each of my routes using this gateway, if the destination
                # is not mentioned in distances, the route disappeared.
                if dest not in distances:
                    del self.routes[dest][via]

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
            logging.info(dest + ' is directly linked to me with cost ' + str(mincost) + '.')

        if mincost != -1:
            logging.info('Found ' + str(len(gateways)) + ' gateways with cost ' + str(mincost) + ': ' + ', '.join(gateways) + '.')
        else:
            logging.info('No route to ' + dest + '.')

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

    def add_route(self, dest, via, cost):
        if dest == self.ip or dest == via or via not in self.links:
            return False

        route_cost = self.links[via] + cost
        self.routes[dest][via] = route_cost

        return True

    def plot(self, path):
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
