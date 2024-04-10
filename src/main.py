import simpy
import matplotlib.pyplot as plt
import random

NUM_NODES = 5 
AREA_X = 10
AREA_Y = 10

#TODO Message type class


class Connection:
    def __init__(self, node1, node2):
        self.node1 = node1
        self.node2 = node2
        self.delay = 0
        self.ETX = 1


class Network:
    def __init__(self, env):
        self.env = env
        self.nodes = []
        self.connections = []
        self.action = env.process(self.run())
    
    def run(self):
        #global NUM_NODES, AREA_X, AREA_Y
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
            plt.plot(node.position[0], node.position[1], 'bo')  # Plot node position
            for neighbor in node.neighbors:
                plt.plot([node.position[0], neighbor.position[0]], [node.position[1], neighbor.position[1]], 'r-')  # Line between neighbors

        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Network Topology')
        plt.grid(True)
        plt.show()

    def generate_nodes(self, env, n = 3, areaX = 10, areaY = 10):
        for i in range(n):
            isLBR = False
            name = 'Node{}'.format(i + 1)
            position = (random.uniform(0, areaX), random.uniform(0, areaY))  # Random position between (0, 0) and (10, 10)
            sigRange = 10
            if i == 0:
                isLBR = True
            node = Node(env, name, position, self, sigRange, isLBR)
            self.add_node(node)

    def distance(self, node1, node2):
        return ((node1.position[0] - node2.position[0])**2 + (node1.position[1] - node2.position[1])**2)**0.5
    
    #Generate connection between nodes based on the distance between them
    def generate_connections(self):
        for node1 in self.nodes:
            for node2 in self.nodes:
                if node1 != node2 and self.distance(node1, node2) <= node1.range:
                    connection = Connection(node1, node2)
                    self.add_connection(connection)

    #Broadcast function, to be called by nodes
    def broadcast(self, node, message):
        for connection in self.connections:
            if connection.node1 == node:
                connection.node2.inbox.append(message)

    

class Node:
    def __init__(self, env, name, position, network, range, isLBR=False):
        self.env = env
        self.name = name
        self.position = position
        self.network = network
        self.range = range
        self.inbox = []
        self.isLBR = isLBR
        self.neighbors = []
        self.action = env.process(self.run())
        

    def run(self):
        
        while True:
            if self.isLBR:
                self.network.broadcast(self, 'Hello from LBR ' + self.name)
            

            while self.inbox:
                message = self.inbox.pop(0)
                #print(self.name + ' received: ' + message)

                #TODO Process message

            yield self.env.timeout(1)
    
    def broadcast(self, message):
        for node in self.network.nodes:
            if node != self and self.distance(node) <= self.range:
                node.inbox.append(message)
    
    def discover_neighbors(self):
        self.neighbors = [node for node in self.network.nodes if node != self and self.distance(node) <= self.range]


def main():
    env = simpy.Environment()
    network = Network(env)
    #for node in nodes:
        #node.discover_neighbors()
    
    env.run(until=10)
    network.plot_network()
    
    


if __name__ == "__main__":
    main()
