#! /usr/bin/env python
from graphviz import *
from collections import defaultdict as dd
from threading import Lock
import logging

class RoutingTable:
    def __init__(self, ip):
        self.routes = dd(lambda: dd(list))
        self.links = dd(lambda: -1)
        self.ip = ip
        self.lock = Lock()

        self.dot = Digraph()
        self.dot.attr(overlap='false')
        self.dot.node('root', label=self.ip)

    def clear(self, via):
        for dest in self.routes:
            if dest == self.ip:
                continue

            if via in self.routes[dest]:
                self.routes[dest][via].clear()

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
        return True

    def del_link(self, ip):
        if ip in links:
            del self.links[ip]

    def update(self, via, distances):
        for dest in distances:
            self.add(dest, via, distances[dest])

    def get_best_gateways(self, dest):
        if dest in self.routes:
            routes = self.routes[dest].items()
            mincost = min(cost for via, cost in routes)
            gateways = [via for via, cost in routes if cost == mincost]
            logging.info('Found ' + str(len(gateways)) + ' gateways with cost ' + str(mincost) + ': ' + ', '.join(gateways) + '.')
        elif dest in self.links:
            gateways = [dest]
            mincost = self.links[dest]
            logging.info(dest + ' is directly linked to me with cost ' + str(mincost) + '.')
        else:
            mincost = -1
            gateways = []
            logging.info('No route to ' + dest + '.')

        return mincost, gateways

    def get_all_best_gateways(self):
        distances = {}

        for dest in self.routes:
            mincost, gateways = self.get_best_gateways(dest)
            if len(gateways) > 0:
                distances[dest] = mincost

        return distances

    def add(self, dest, via, cost):
        if dest == self.ip or dest == via or via not in self.links:
            return False

        weight = self.links[via]
        self.routes[dest][via].append(cost + weight)

        return True

    def plot(self, path):
        for link in self.links:
            self.dot.node(link, label=link)
            self.dot.edge('root', link, label=str(self.links[link]))

        for dest in self.routes:
            for via in self.routes[dest]:
                for cost in self.routes[dest][via]:
                    self.dot.edge(via, dest, label=str(cost - self.links[via]))

        self.dot.render(path)

    def show_links(self):
        print('ADDRESS\tWEIGHT')
        for dest in self.links:
            print(dest + '\t' + str(self.links[dest]))

    def show_routes(self):
        print(self)

    def __str__(self):
        tbl = 'DESTINATION\tGATEWAY IP\tCOST\n'
        for dest in self.routes:
            for via in self.routes[dest]:
                for cost in self.routes[dest][via]:
                    tbl += dest + '\t' + via + '\t' + str(cost) + '\n'

        return tbl
