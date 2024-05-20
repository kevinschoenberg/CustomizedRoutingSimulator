import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import random

from connection import Connection
from message import Message
from node import Node


random.seed(0)

NUM_NODES = 10
AREA_X = 3
AREA_Y = 3
class Network:
    def __init__(self, env):
        self.env = env
        self.nodes = []
        self.connections = []
        self.action = env.process(self.run())

    def run(self):
        # global NUM_NODES, AREA_X, AREA_Y
        self.generate_nodes(self.env, NUM_NODES, AREA_X, AREA_Y)
        self.generate_connections()

        while True:
            yield self.env.timeout(1)

    def add_node(self, node):
        self.nodes.append(node)

    def add_connection(self, connection):
        self.connections.append(connection)

    def remove_node(self, node):
        self.nodes.remove(node)

    def remove_connection(self, connection):
        self.connections.remove(connection)

    def plot_network(self):
        plt.figure(figsize=(8, 6))
        for node in self.nodes:
            # Write the node ID and rank on the plot with some separation
            plt.text(node.position[0] + 0.1, node.position[1], f"{node.node_id}", fontsize=12, color='blue',
                     weight='bold', zorder=2)
            plt.text(node.position[0] - 0.1, node.position[1], f"{node.rank}", fontsize=12, color='green',
                     weight='bold', zorder=2)
            plt.plot(node.position[0], node.position[1], 'bo')  # Plot node position
            for neighbor_id in node.neighbors:
                for node2 in self.nodes:
                    if node2.node_id == neighbor_id:
                        # plt.plot([node.position[0], node2.position[0]], [node.position[1], node2.position[1]], 'r-', zorder=1)  # Line between neighbors
                        pass
        # draw an arrow from each node to their parent
        for node in self.nodes:
            if node.parent is not None:
                for parent in self.nodes:
                    if parent.node_id == node.parent:
                        plt.arrow(node.position[0], node.position[1], 0.9 * (parent.position[0] - node.position[0]),
                                  0.9 * (parent.position[1] - node.position[1]), head_width=0.05, head_length=0.1,
                                  fc='k', ec='k', zorder=3)

        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Network Topology')
        # Create custom legend elements
        blue_dot = mlines.Line2D([], [], color='blue', marker='o', markersize=10, label='ID')
        green_dot = mlines.Line2D([], [], color='green', marker='o', markersize=10, label='Rank')

        # Add legend with custom legend elements
        plt.legend(handles=[blue_dot, green_dot], loc='upper left')
        # plt.grid(True)
        plt.show()

    def generate_nodes(self, env, n=3, areaX=10, areaY=10):
        # create a function that returns coordinates in a triangle based on number of nodes n and the current node i
        def get_ith_node_position(n, i):
            if i > n or i < 1:
                return "Invalid node index"  # Check if the node index is out of bounds

            positions = []
            current_level, total_nodes = 1, 0

            # Generate positions for nodes in the pyramid
            while total_nodes < n:
                start_x = -(current_level - 1) / 2
                for node in range(current_level):
                    total_nodes += 1
                    positions.append(((start_x + node), -1 * (current_level - 1)))
                    if total_nodes == n:
                        break
                current_level += 1

            return positions[i - 1]

        for i in range(n):
            isLBR = False
            name = 'Node{}'.format(i)

            # position = get_ith_node_position(n, i + 1)
            position = (random.uniform(0, areaX), random.uniform(0, areaY))

            sigRange = 1.3
            if i == 0:
                isLBR = True
            node = Node(env, name, position, self, sigRange, i, isLBR=isLBR)
            self.add_node(node)

    def distance(self, node1, node2):
        return ((node1.position[0] - node2.position[0]) ** 2 + (node1.position[1] - node2.position[1]) ** 2) ** 0.5

    # Generate connection between nodes based on the distance between them
    def generate_connections(self):
        for node1 in self.nodes:
            for node2 in self.nodes:
                if node1 != node2 and self.in_range(node1, node2):
                    etx = self.distance(node1, node2)
                    connection = Connection(node1, node2, etx=etx)
                    self.add_connection(connection)

        for connection in self.connections:
            if connection.node1.node_id in [4, 1] and connection.node2.node_id in [4, 1]:
                print("removing ", connection.node1.node_id, connection.node2.node_id)
                self.remove_connection(connection)

    # Broadcast function, to be called by nodes
    def broadcast(self, node, message):
        for connection in self.connections:
            if connection.node1 == node:
                connection.node2.inbox.append(message)

    def send_message(self, sender, node_id, message):
        [node.inbox.append(message) for node in self.nodes if node.node_id == node_id and self.in_range(sender, node)]

    def in_range(self, node1, node2):
        return self.distance(node1, node2) <= node1.range

    def get_node(self, node_id):
        return [node for node in self.nodes if node.node_id == node_id][0]