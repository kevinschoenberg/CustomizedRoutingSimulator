import simpy
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import random

from network import Network
from node import Node
from connection import Connection
from message import Message

def main():
    env = simpy.Environment()
    network = Network(env)

    #for node in nodes:
        #node.discover_neighbors()
    
    env.run(until=50)
    network.plot_network()

    #print the parent candidates fo each node
    for node in network.nodes:
        print(node.name + ' parent candidates: ' + str(node.parent_candidates))
        print(node.name + ' rank: ' + str(node.rank))
        print('-----------------------------------')
    for node in network.nodes:
        #if node.isLBR:
        print(node.name + ' routing table: ' + str(node.routing_table))
        print('-----------------------------------')


if __name__ == "__main__":
    main()
