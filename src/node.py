import math

from message import Message

from collections import Counter

class Node:
    def __init__(self, env, name, position, network, node_range, node_id, heartbeat_interval, is_lbr=False, log=False):
        self.env = env
        self.name = name
        self.position = position
        self.network = network
        self.range = node_range
        self.isLBR = is_lbr
        self.node_id = node_id
        self.log = log
        self.heartbeat_interval = heartbeat_interval
        self.action = env.process(self.run())

        self.inbox = []
        self.neighbors = {}
        self.last_beat = self.env.now
        self.rank = None
        self.DAGrank = None
        self.parent_candidates = {}
        self.parent = None
        self.instanceID = 0
        self.routing_table = {}
        self.last_dodag = -79
        self.alive = True
        self.last_gr = 0
        self.ip_routing_table = {}
        self.ip_address = None
        self.ip_prefix = None

    def update_ip_routing_table(self):
        self.ip_routing_table = {}
        ip_address = None
        ip_prefix = None
        temp = 0
        for value in Counter(self.routing_table.values()).keys():
            temp += 1
            if self.isLBR:
                ip_address = f'2001:{hex(temp)[2:]}'
                ip_prefix = 16 + len(hex(temp)[2:])*4
            if not self.isLBR and self.ip_prefix is not None:
                if ((len(self.ip_address)-(math.floor(len(self.ip_address)/5))) % 4 > 0):
                    ip_address = f'{self.ip_address}{hex(temp)[2:]}'
                else:
                    ip_address = f'{self.ip_address}:{hex(temp)[2:]}'
                ip_prefix = self.ip_prefix + len(hex(temp)[2:])*4
            if ip_address is not None:
                #Send DIO message to Node with id = value, informing them of their subnet
                self.network.send_message(self, value, Message("DIO", {'DAGrank': self.DAGrank, 'rank': self.rank, 'routing_table': self.routing_table, 'instanceID': self.instanceID, 'ip_address': ip_address, 'prefix': ip_prefix}, self.node_id))
                #Update the nodes ip routing table
                self.ip_routing_table[f'{ip_address}::/{ip_prefix}'] = value
        #print(f'MAC: Node {self.node_id} Routing Table {self.routing_table.items()}')
        print(f'IP: Node {self.node_id} ip routing table = {self.ip_routing_table.items()}')

    def run(self):
        self.network.broadcast(self, Message("ND", None, self.node_id))
        if self.isLBR:
            self.rank = 0
            self.DAGrank = 0
        while self.alive:

            if self.log:
                print(f"neighbors of {self.node_id}: {self.neighbors}")

            # Root node periodically initiates new DODAG
            if self.isLBR:
                if self.env.now - self.last_dodag > 80:
                    print(f"Node {self.node_id} is sending DIO")
                    self.instanceID += 1
                    self.routing_table = {}
                    for neighbor in self.neighbors.keys():
                        self.network.send_message(self, neighbor, Message("DIO", {'rank': self.rank,
                                                                                  'instanceID': self.instanceID,
                                                                                  'routing_table': self.routing_table,
                                                                                  'ip_address': None,
                                                                                  'prefix': None},
                                                                          self.node_id))
                    self.last_dodag = self.env.now

            # Process incoming messages
            while self.inbox:
                message: Message = self.inbox.pop(0)
                match message.message_type:
                    case "ND":
                        self.network.send_message(self, message.sender_id, Message("ACK", None, self.node_id))
                    case "ACK":
                        self.neighbors[message.sender_id] = self.env.now
                        if self.node_id == 0:
                            if self.log:
                                print(self.neighbors)
                    case "DIO":
                        if message.payload['instanceID'] > self.instanceID:
                            self.instanceID = message.payload['instanceID']
                            self.parent_candidates = {}
                            self.last_gr = 0
                            self.parent = None
                            self.rank = None
                            self.DAGrank = None

                        if message.payload['ip_address'] is not None and len(self.routing_table) > 0:
                            self.ip_address = message.payload['ip_address']
                            self.ip_prefix = message.payload['prefix']
                            self.update_ip_routing_table()

                        if self.DAGrank is None or self.DAGrank >= message.payload['DAGrank']:
                            # only add if it is not already on the list

                            self.parent_candidates[message.sender_id] = self.objective_function(message.payload['rank'],
                                                                                                self.network.get_connection_metrics(
                                                                                                    self.node_id,
                                                                                                    message.sender_id))
                            self.routing_table = {}

                            if self.isLBR:
                                yield self.env.timeout(0.002)
                            else:
                                yield self.env.timeout(0.02)
                        yield self.env.timeout(0.002)
                    case "DAO":

                        self.update_routing_table(message.payload['routing_table'], message.sender_id)

                        if self.parent is not None:
                            self.network.send_message(self, self.parent,
                                                      Message("DAO", {'routing_table': self.routing_table},
                                                              self.node_id))
                        if self.isLBR and len(self.routing_table) > 0:
                                    self.update_ip_routing_table()
                        if self.isLBR:
                            yield self.env.timeout(0.002)
                        else:
                            yield self.env.timeout(0.002)
                    case "DAO-ACK":
                        # If approoved
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
                                self.network.send_message(self, neighbor, Message("DIO", {'DAGrank': self.DAGrank,
                                                                                          'rank': self.rank,
                                                                                          'instanceID': self.instanceID,
                                                                                          'routing_table': self.routing_table,
                                                                                          'ip_address': None,
                                                                                          'prefix': None},
                                                                                  self.node_id))
                            self.last_dodag = self.env.now
                        else:
                            if not message.payload['nr'] > self.last_gr:
                                self.last_gr = message.payload['nr']
                                for neighbor in self.neighbors.keys():
                                    self.network.send_message(self, neighbor,
                                                              Message("GR", {'nr': message.payload['nr'] + 1},
                                                                      self.node_id))
                        if self.isLBR:
                            yield self.env.timeout(0.002)
                        else:
                            yield self.env.timeout(0.02)

            # Send heartbeat messages to neighbors
            if self.env.now - self.last_beat > self.heartbeat_interval:
                for neighbor in self.neighbors.keys():
                    self.network.send_message(self, neighbor, Message("HB", None, self.node_id))
                self.last_beat = self.env.now

            # Check if the parent should be updated (LBR has no parent)
            if not self.isLBR:
                old_parent = self.parent
                self.update_parent()
                if old_parent != self.parent or old_parent is None:
                    # Send DAO message to parent, if a new one is selected
                    self.network.send_message(self, self.parent,
                                              Message("DAO", {'routing_table': self.routing_table}, self.node_id))

                    if self.DAGrank is not None:
                        for neighbor in self.neighbors.keys():
                            self.network.send_message(self,
                                                      neighbor,
                                                      Message("DIO",
                                                              {'DAGrank': self.DAGrank,
                                                               'rank': self.rank,
                                                               'routing_table': self.routing_table,
                                                               'instanceID': self.instanceID,
                                                               'ip_address': None,
                                                               'prefix': None},
                                                              self.node_id))

            # Check if neighbors are still alive
            for node in list(self.neighbors.keys()):
                if self.env.now - self.neighbors[node] > self.heartbeat_interval * 2:
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
                        self.network.send_message(self, self.parent,
                                                  Message("DAO", {'routing_table': self.routing_table}, self.node_id))

                    if node in self.parent_candidates:
                        del self.parent_candidates[node]

            # Check if parent is still alive
            if self.parent not in self.neighbors.keys() and self.parent is not None:
                self.parent = None
                self.update_parent()
                if self.parent is None:
                    print(f"Node {self.node_id} sending GR")
                    for neighbor in self.neighbors.keys():
                        self.network.send_message(self, neighbor, Message("GR", {'nr': 0}, self.node_id))
                else:
                    self.network.send_message(self, self.parent,
                                              Message("DAO", {'routing_table': self.routing_table}, self.node_id))

            yield self.env.timeout(0.1)


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
