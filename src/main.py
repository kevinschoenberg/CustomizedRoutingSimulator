import simpy
import matplotlib.pyplot as plt
import random

NUM_NODES = 40
AREA_X = 10
AREA_Y = 10


class Message:
    def __init__(self, message_type, payload, sender_id):
        self.message_type = message_type
        self.payload = payload
        self.sender_id = sender_id


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
            plt.plot(node.position[0], node.position[1], 'bo')  # Plot node position
            for neighbor_id in node.neighbors:
                for node2 in self.nodes:
                    if node2.node_id == neighbor_id:
                        plt.plot([node.position[0], node2.position[0]], [node.position[1], node2.position[1]], 'r-')  # Line between neighbors

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
            sigRange = 2
            if i == 0:
                isLBR = True
            node = Node(env, name, position, self, sigRange, i, isLBR=isLBR)
            self.add_node(node)

    def distance(self, node1, node2):
        return ((node1.position[0] - node2.position[0])**2 + (node1.position[1] - node2.position[1])**2)**0.5
    
    #Generate connection between nodes based on the distance between them
    def generate_connections(self):
        for node1 in self.nodes:
            for node2 in self.nodes:
                if node1 != node2 and self.in_range(node1, node2):
                    connection = Connection(node1, node2)
                    self.add_connection(connection)

    #Broadcast function, to be called by nodes
    def broadcast(self, node, message):
        for connection in self.connections:
            if connection.node1 == node:
                connection.node2.inbox.append(message)

    def send_message(self, sender, node_id, message):
        [node.inbox.append(message) for node in self.nodes if node.node_id == node_id and self.in_range(sender, node)]

    def in_range(self, node1, node2):
        return self.distance(node1, node2) <= node1.range
    

class Node:
    def __init__(self, env, name, position, network, range, node_id, isLBR=False):
        self.env = env
        self.name = name
        self.position = position
        self.network = network
        self.range = range
        self.inbox = []
        self.isLBR = isLBR
        self.node_id = node_id
        self.neighbors = []
        # parent candidates
        # parent (max parent candidate)
        # objective function (parent selection)


        self.action = env.process(self.run())

    def run(self):
        self.network.broadcast(self, Message("ND", None, self.node_id))
        while True:
            #if self.isLBR:
                #self.network.broadcast(self, 'Hello from LBR ' + self.name)

            while self.inbox:
                message: Message = self.inbox.pop(0)

                match message.message_type:
                    case "ND":
                        # Received ND message
                        self.network.send_message(self, message.sender_id, Message("ACK", None, self.node_id))
                        yield self.env.timeout(0.1)
                    case "ACK":
                        self.neighbors.append(message.sender_id)
                        yield self.env.timeout(0.1)
                    case "DIO":
                        pass
                    case "DAO":
                        pass
                    case "DIS":  # Optional
                        pass


                #print(self.name + ' received: ' + message)

                #TODO Process message

            yield self.env.timeout(1)


def main():
    env = simpy.Environment()
    network = Network(env)
    #for node in nodes:
        #node.discover_neighbors()
    
    env.run(until=10)
    network.plot_network()
    
    


if __name__ == "__main__":
    main()
