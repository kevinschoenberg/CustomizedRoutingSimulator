import simpy
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import random
from matplotlib.animation import FuncAnimation

from network import Network
from node import Node
from connection import Connection
from message import Message

NUM_NODES = 20
AREA_X = 5
AREA_Y = 5
PLOT_INTERVAL = 5

HEARTBEAT_INTERVAL = 20

DIS_INTERVAL = 5


def main():
    env = simpy.Environment()
    network = Network(env, NUM_NODES, AREA_X, AREA_Y, HEARTBEAT_INTERVAL, PLOT_INTERVAL, DIS_INTERVAL)

    env.run(until=200)

    # print the parent candidates fo each node
    for node in network.nodes:
        print(node.name + ' parent candidates: ' + str(node.parent_candidates))
        print(node.name + ' rank: ' + str(node.rank))
        print('-----------------------------------')
    for node in network.nodes:
        #if node.isLBR:
        print(node.name + ' routing table: ' + str(node.routing_table))
        print('-----------------------------------')
        print(node.name + ' ip routing table: ' + str(node.ip_routing_table))
        print('-----------------------------------')
        print(node.name + ' subnet routing table: ' + str(node.subnet_routing_table))
        print('-----------------------------------')
    plt.show()


if __name__ == "__main__":
    main()
