import simpy
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import random

NUM_NODES = 10
AREA_X = 3
AREA_Y = 3


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
            # Write the node ID and rank on the plot with some separation
            plt.text(node.position[0] + 0.1, node.position[1], f"{node.node_id}", fontsize=12, color='blue', weight='bold', zorder=2)
            plt.text(node.position[0] - 0.1, node.position[1], f"{node.rank}", fontsize=12, color='green', weight='bold', zorder=2)
            plt.plot(node.position[0], node.position[1], 'bo')  # Plot node position
            for neighbor_id in node.neighbors:
                for node2 in self.nodes:
                    if node2.node_id == neighbor_id:
                        plt.plot([node.position[0], node2.position[0]], [node.position[1], node2.position[1]], 'r-', zorder=1)  # Line between neighbors

        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Network Topology')
         # Create custom legend elements
        blue_dot = mlines.Line2D([], [], color='blue', marker='o', markersize=10, label='ID')
        green_dot = mlines.Line2D([], [], color='green', marker='o', markersize=10, label='Rank')
        
        # Add legend with custom legend elements
        plt.legend(handles=[blue_dot, green_dot], loc='upper left')
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

    def get_node(self, node_id):
        return [node for node in self.nodes if node.node_id == node_id][0]
    

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
        self.rank = None
        self.parent_candidates = []
        self.parent = None
        self.instanceID = 0
        self.routing_table = []
        # objective function (parent selection)


        self.action = env.process(self.run())

    def run(self):
        self.network.broadcast(self, Message("ND", None, self.node_id))
        while True:
            if self.isLBR:
                self.rank = 0
                for neighbor in self.neighbors:
                    self.network.send_message(self, neighbor, Message("DIO", {'rank': self.rank, 'instanceID': self.instanceID}, self.node_id))

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
                        # add to parent candidates if the rank is not higher than the current rank
                        if self.rank is None or self.rank > self.network.get_node(message.sender_id).rank:
                            # only add if it is not already on the list
                            if message.sender_id not in self.parent_candidates:
                                self.parent_candidates.append({"senderid": message.sender_id, "rank": message.payload['rank']})
                            # Update rank and send DIO message to neighbors
                            self.rank = message.payload['rank'] + 1
                            for neighbor in self.neighbors:
                                self.network.send_message(self, neighbor, Message("DIO", {'rank': self.rank}, self.node_id))

                            
                            # Choose parent from parent candidates by choosing parent with the lowest rank
                            self.parent_candidates.sort(key=lambda x: x['rank'])
                            self.parent = self.parent_candidates[0]['senderid']
                            # Send DAO message to parent
                            self.network.send_message(self, self.parent, Message("DAO", self.routing_table, self.node_id))
                    case "DAO":
                        #if the payload is empty add the sender to routing table
                        if not message.payload and self.isLBR == False:
                            self.routing_table.append({'destination': message.sender_id, 'nexthop': message.sender_id})
                            # Send DAO-ACK message to sender of DAO message including this nodes parent
                            self.network.send_message(self, message.sender_id, Message("DAO-ACK", None, self.node_id))
                        else:
                            for sender_routing_entry in message.payload:
                                sender_destination = sender_routing_entry['destination']
                                found_match = False
                                for entry in self.routing_table:
                                    if sender_destination == entry['destination']:
                                        found_match = True
                                if not found_match:
                                    # If the payloads destination is not in the routing table, add it
                                    self.routing_table.append({'destination': sender_routing_entry['destination'], 'nexthop': message.sender_id})
                                    # Send DAO-ACK message to sender of DAO message including this nodes parent
                                    self.network.send_message(self, message.sender_id, Message("DAO-ACK", None, self.node_id))
                    case "DAO-ACK":
                        #If approoved
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
    
    env.run(until=50)
    network.plot_network()

    #print the parent candidates fo each node
    for node in network.nodes:
        print(node.name + ' parent candidates: ' + str(node.parent_candidates))
        print(node.name + ' rank: ' + str(node.rank))
        print('-----------------------------------')
    for node in network.nodes:
        if node.isLBR:
            print(node.name + ' routing table: ' + str(node.routing_table))
            print('-----------------------------------')
    


if __name__ == "__main__":
    main()
