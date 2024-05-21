import simpy
import time
import math

from message import Message


class Node:
    def __init__(self, env, name, position, network, range, node_id, isLBR=False, log=False):
        self.env= env
        self.name = name
        self.position = position
        self.network = network
        self.range = range
        self.inbox = []
        self.isLBR = isLBR
        self.node_id = node_id
        self.neighbors = {}
        self.last_beat = self.env.now
        self.rank = None
        self.DAGrank = None
        self.parent_candidates = {}
        self.parent = None
        self.instanceID = 0
        self.routing_table = {}
        self.last_dio = -39
        self.alive = True
        self.last_gr = 0
        self.log = log

        # objective function (parent selection)

        self.action = env.process(self.run())

    def update_routing_table(self, routing_table, sender_id):
        keys_to_delete = []
        for key, value in self.routing_table.items():
            if value == sender_id:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            self.routing_table.pop(key)

        for key, _ in routing_table.items():
            self.routing_table[key] = sender_id

        self.routing_table[sender_id] = sender_id

    @staticmethod
    def objective_function(parent_rank, rank_step):
        rank_factor = 1
        rank_stretch = 0
        min_hop_rank_increase = 256

        rank_increase = (rank_step * rank_factor + rank_stretch) * min_hop_rank_increase

        return parent_rank + rank_increase


    def update_parent(self):
        if len(self.parent_candidates.keys()) > 0:
            best_parent_candidate_rank = 9999999
            best_parent_candidate = None
            for parent_candidate in self.parent_candidates.keys():
                if self.parent_candidates[parent_candidate] < best_parent_candidate_rank:
                    best_parent_candidate = parent_candidate
                    best_parent_candidate_rank = self.parent_candidates[parent_candidate]

            if self.parent is None or best_parent_candidate_rank < self.parent_candidates[self.parent]:
                self.parent = best_parent_candidate
                self.rank = best_parent_candidate_rank
                self.DAGrank = math.floor(self.rank / 256)
        else:
            self.parent = None
            self.rank = None
            self.DAGrank = None

    def run(self):
        self.network.broadcast(self, Message("ND", None, self.node_id))
        if self.isLBR:
            self.rank = 0
            self.DAGrank = 0
        while self.alive:
            if self.isLBR:
                if self.env.now - self.last_dio > 40:
                    if self.log:
                        print(f"Node {self.node_id} is sending DIO")
                    self.instanceID += 1
                    self.routing_table = {}
                    for neighbor in self.neighbors.keys():
                        self.network.send_message(self, neighbor, Message("DIO", {'rank': self.rank, 'instanceID': self.instanceID, 'routing_table': self.routing_table}, self.node_id))
                    self.last_dio = self.env.now

            if self.env.now - self.last_beat > 5:
                for neighbor in self.neighbors.keys():
                    self.network.send_message(self, neighbor, Message("HB", None, self.node_id))
                self.last_beat = self.env.now

            while self.inbox:
                message: Message = self.inbox.pop(0)

                match message.message_type:
                    case "ND":
                        self.network.send_message(self, message.sender_id, Message("ACK", None, self.node_id))
                        yield self.env.timeout(0.1)
                    case "ACK":
                        self.neighbors[message.sender_id] = self.env.now
                        if self.node_id == 0:
                            if self.log:
                                print(self.neighbors)
                        yield self.env.timeout(0.1)
                    case "DIO":
                        if message.payload['instanceID'] > self.instanceID:
                            self.instanceID = message.payload['instanceID']
                            self.parent_candidates = {}
                            self.last_gr = 0
                            self.parent = None
                            self.rank = None
                            self.DAGrank = None
                            #self.routing_table = {}

                        if self.DAGrank is None or self.DAGrank > self.network.get_node(message.sender_id).DAGrank:
                            # only add if it is not already on the list
                            self.parent_candidates[message.sender_id] = self.objective_function(message.payload['rank'], self.network.get_connection_metrics(self.node_id, message.sender_id))

                            self.update_parent()

                            self.routing_table = {}

                            for neighbor in self.neighbors.keys():
                                self.network.send_message(self, neighbor, Message("DIO", {'rank': self.rank, 'routing_table': self.routing_table, 'instanceID': self.instanceID}, self.node_id))


                        #poison response
                        if message.sender_id == self.parent and message.payload['rank'] > self.rank:
                            for neighbor in self.neighbors.keys():
                                self.network.send_message(self, neighbor, Message("DIO", {'rank': self.rank, 'routing_table': self.routing_table, 'instanceID': self.instanceID}, self.node_id))

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

                    case "HB":
                        self.neighbors[message.sender_id] = self.env.now

                    case "GR":
                        if self.isLBR:
                            self.instanceID += 1
                            if self.log:
                                print(f"Node {self.node_id} is sending DIO")
                            self.routing_table = {}
                            for neighbor in self.neighbors.keys():
                                self.network.send_message(self, neighbor, Message("DIO", {'rank': self.rank, 'instanceID': self.instanceID, 'routing_table': self.routing_table},self.node_id))
                            self.last_dio = self.env.now
                        else:
                            if not message.payload['nr'] > self.last_gr:
                                self.last_gr = message.payload['nr']
                                for neighbor in self.neighbors.keys():
                                    self.network.send_message(self, neighbor, Message("GR", {'nr': message.payload['nr'] + 1}, self.node_id))



            # check if any storage nodes have not sent a heartbeat in the last 20 seconds
            for node in list(self.neighbors.keys()):
                if self.env.now - self.neighbors[node] > 10:
                    if self.log:
                        print(f"Node {self.node_id} removing neighbor {node}")
                    del self.neighbors[node]

                    keys_to_delete = []
                    for key, value in self.routing_table.items():
                        if value == node or key == node:
                            keys_to_delete.append(key)

                    for key in keys_to_delete:
                        self.routing_table.pop(key)

                    if self.parent is not None:
                        self.network.send_message(self, self.parent, Message("DAO", {'routing_table': self.routing_table}, self.node_id))

                    if node in self.parent_candidates:
                        del self.parent_candidates[node]

            if self.parent not in self.neighbors.keys() and self.parent is not None:
                self.parent = None
                self.update_parent()
                if self.parent is None:
                    for neighbor in self.neighbors.keys():
                        self.network.send_message(self, neighbor, Message("GR", {'nr': 0}, self.node_id))
                else:
                    self.network.send_message(self, self.parent, Message("DAO", {'routing_table': self.routing_table}, self.node_id))

            yield self.env.timeout(1)