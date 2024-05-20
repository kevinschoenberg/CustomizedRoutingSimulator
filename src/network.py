import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import random
from matplotlib.animation import FuncAnimation

from connection import Connection
from message import Message
from node import Node


random.seed(0)

NUM_NODES = 10
AREA_X = 3
AREA_Y = 3
PLOT_INTERVAL = 0.1

class Network:
    def __init__(self, env):
        self.env = env
        self.nodes = []
        self.connections = []
        self.remove = True
        self.action = env.process(self.run())
        self.plot_action = env.process(self.update_plot())
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.plot_count = 0

    def run(self):
        # global NUM_NODES, AREA_X, AREA_Y
        self.generate_nodes(self.env, NUM_NODES, AREA_X, AREA_Y)
        self.generate_connections()

        while True:
            if self.env.now > 40 and self.remove:
                print(f"Removing node {self.nodes[7].node_id}")
                self.nodes[7].alive = False
                self.remove = False
            yield self.env.timeout(3)
    
    def update_plot(self):
        while True:
            self.plot_network()
            yield self.env.timeout(PLOT_INTERVAL)


    def add_node(self, node):
        self.nodes.append(node)

    def add_connection(self, connection):
        self.connections.append(connection)

    def remove_node(self, node):
        #delete node instance and remove connections
        for connection in self.connections:
            if connection.node1 == node or connection.node2 == node:
                self.remove_connection(connection)

        self.nodes.remove(node)

    def remove_connection(self, connection):
        self.connections.remove(connection)

    def plot_network(self):
            self.ax.clear()
            self.plot_count += 1
            for node in self.nodes:
                # Write the node ID and rank on the plot with some separation
                self.ax.text(node.position[0] + 0.1, node.position[1], f"{node.node_id}", fontsize=12, color='blue',
                            weight='bold', zorder=2)
                self.ax.text(node.position[0] - 0.1, node.position[1], f"{node.rank}", fontsize=12, color='green',
                            weight='bold', zorder=2)

                if node.alive:
                    self.ax.plot(node.position[0], node.position[1], 'bo')  # Plot node position
                else:
                    self.ax.plot(node.position[0], node.position[1], 'ro')
                for neighbor_id in node.neighbors:
                    for node2 in self.nodes:
                        if node2.node_id == neighbor_id:
                            # self.ax.plot([node.position[0], node2.position[0]], [node.position[1], node2.position[1]], 'r-', zorder=1)  # Line between neighbors
                            pass
            # draw an arrow from each node to their parent
            for node in self.nodes:
                if node.alive and node.parent is not None:
                    for parent in self.nodes:
                        if parent.node_id == node.parent:
                            self.ax.arrow(node.position[0], node.position[1], 0.9 * (parent.position[0] - node.position[0]),
                                        0.9 * (parent.position[1] - node.position[1]), head_width=0.05, head_length=0.1,
                                        fc='k', ec='k', zorder=3)

            self.ax.set_xlabel('X')
            self.ax.set_ylabel('Y')
            self.ax.set_title('Network Topology')
            self.ax.text(0.5, 1.05, f"Plot Update Count: {self.plot_count}", transform=self.ax.transAxes,
                     fontsize=14, color='red', weight='bold', ha='center')
            # Create custom legend elements
            blue_dot = mlines.Line2D([], [], color='blue', marker='o', markersize=10, label='ID')
            green_dot = mlines.Line2D([], [], color='green', marker='o', markersize=10, label='Rank')

            # Add legend with custom legend elements
            self.ax.legend(handles=[blue_dot, green_dot], loc='upper left')
            plt.draw()
            plt.pause(0.01)

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