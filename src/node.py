import simpy
import network

from message import Message


class Node:
    def __init__(self, env, name, position, network, range, node_id, isLBR=False):
        self.env= env
        self.name = name
        self.position = position
        self.network = network
        self.range = range
        self.inbox = []
        self.isLBR = isLBR
        self.node_id = node_id
        self.neighbors = []
        self.rank = None
        self.parent_candidates = {}
        self.parent = None
        self.instanceID = 0
        self.routing_table = {}
        # objective function (parent selection)


        self.action = env.process(self.run())

    def update_routing_table(self, routing_table, sender_id):
        #update incomming routing table using the sender id as next hop if a new destiantion is found
        for key, value in routing_table.items():
            if key not in self.routing_table:
                self.routing_table[key] = sender_id
        if sender_id not in self.routing_table:
            self.routing_table[sender_id] = sender_id

    def run(self):
        self.network.broadcast(self, Message("ND", None, self.node_id))
        if self.isLBR:
            self.rank = 0
        while True:

            if self.isLBR:
                for neighbor in self.neighbors:
                    self.network.send_message(self, neighbor, Message("DIO", {'rank': self.rank, 'instanceID': self.instanceID, 'routing_table': self.routing_table}, self.node_id))

            while self.inbox:
                message: Message = self.inbox.pop(0)

                match message.message_type:
                    case "ND":
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
                                self.parent_candidates[message.sender_id] = message.payload['rank']
                            # Update rank and send DIO message to neighbors
                            self.rank = message.payload['rank'] + 1

                            for neighbor in self.neighbors:
                                self.network.send_message(self, neighbor, Message("DIO", {'rank': self.rank, 'routing_table': self.routing_table}, self.node_id))

                            #choose the parent with the lowest rank from the dictionary #### TODO CHANGE TO USE OBJECTIVE FUNCTION ####
                            self.parent = min(self.parent_candidates, key=self.parent_candidates.get)
                            if self.parent_candidates[self.parent] is not None:
                                self.rank = self.parent_candidates[self.parent] + 1

                        #self.update_routing_table(message.payload['routing_table'], message.sender_id)

                        # Send DAO message to parent
                        self.network.send_message(self, self.parent, Message("DAO", {'routing_table': self.routing_table}, self.node_id))
                    case "DAO":

                        self.update_routing_table(message.payload['routing_table'], message.sender_id)

                        if self.parent is not None:
                            self.network.send_message(self, self.parent, Message("DAO", {'routing_table': self.routing_table}, self.node_id))
                    case "DAO-ACK":
                        #If approoved
                        pass

                    case "DIS":  # Optional
                        pass


            yield self.env.timeout(1)