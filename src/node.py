import math
from collections import Counter

from message import Message

from collections import Counter
import random

class Node:
    def __init__(self, env, name, position, network, node_range, node_id, heartbeat_interval, dis_interval, is_lbr=False, log=False):
        self.env = env
        self.name = name
        self.position = position
        self.network = network
        self.range = node_range
        self.isLBR = is_lbr
        self.node_id = node_id
        self.log = log
        self.heartbeat_interval = heartbeat_interval
        self.dis_interval = dis_interval
        self.action = env.process(self.run())
        self.original_dis_interval = self.dis_interval

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
        self.log = log
        self.sent_dio = False
        self.grounded = False
        self.last_dis = 0
        self.dis_count = 0

        self.last_ip = 0
        self.ip_routing_table = {}
        self.subnet_routing_table = {}
        self.ip_address = None
        self.subnet = None
        self.ip_prefix = None
        self.received_DAO = False

    def update_ip_routing_table(self):
        self.ip_routing_table = {}
        self.subnet_routing_table = {}
        ip_address = None
        ip_prefix = None
        subnet = None
        ip_temp = 0
        subnet_temp = 0
        if self.isLBR:
            ip_temp += 1
            self.subnet = '2001:'
            self.ip_address = f'2001::{ip_temp}'

        for value in Counter(self.routing_table.values()).keys():
            ip_temp += 1
            subnet_temp += 1
            if self.isLBR:
                subnet = f'2001:{hex(subnet_temp)[2:]}'
                ip_prefix = 16 + len(hex(subnet_temp)[2:]) * 4
                ip_address = f'2001::{hex(ip_temp)[2:]}'
            if not self.isLBR and self.ip_prefix is not None:
                ip_address = f'{self.subnet}::{hex(ip_temp)[2:]}'
                if ((len(self.subnet) - (math.floor(len(self.subnet) / 5))) % 4 > 0):
                    subnet = f'{self.subnet}{hex(subnet_temp)[2:]}'
                else:
                    subnet = f'{self.subnet}:{hex(subnet_temp)[2:]}'
                ip_prefix = self.ip_prefix + len(hex(subnet_temp)[2:]) * 4
            if subnet is not None and self.rank is not None:
                #Send DIO message to Node with id = value, informing them of their subnet
                self.network.send_message(self, value, Message("DIO", {'DAGrank': self.DAGrank, 'rank': self.rank,
                                                                       'routing_table': self.routing_table,
                                                                       'instanceID': self.instanceID, 'subnet': subnet,
                                                                       'ip_address': ip_address, 'prefix': ip_prefix, 'grounded': self.grounded},
                                                               self.node_id))
                #Update the nodes ip routing table
                self.subnet_routing_table[f'{subnet}::/{ip_prefix}'] = ip_address
                self.ip_routing_table[ip_address] = value
        #if self.log:
            #print(f"MAC: Node {self.node_id} routing table = {self.routing_table.items()}")
            #print(f'IP: Node {self.node_id} ip routing table = {self.ip_routing_table.items()}')
            #print(f'IP: Node {self.node_id} subnet routing table = {self.subnet_routing_table.items()}')

    def run(self):
        self.dis_interval *= random.uniform(1, 4)
        self.original_dis_interval = self.dis_interval
        self.network.broadcast(self, Message("ND", None, self.node_id))
        if self.isLBR:
            self.rank = 0
            self.DAGrank = 0
            self.grounded = True
        while self.alive:
            # Root node periodically initiates new DODAG
            if self.isLBR:
                if self.env.now - self.last_dodag > 80:
                    print(f"Node {self.node_id} is sending DIO")
                    self.instanceID += 1
                    self.routing_table = {}
                    for neighbor in self.neighbors.keys():
                        self.network.send_message(self, neighbor, Message("DIO", {'DAGrank': self.DAGrank, 'rank': self.rank,
                                                                                  'instanceID': self.instanceID,
                                                                                  'routing_table': self.routing_table,
                                                                                  'ip_address': None,
                                                                                  'subnet': None,
                                                                                  'prefix': None,
                                                                                  'grounded': self.grounded},
                                                                          self.node_id))
                    self.last_dodag = self.env.now
                if self.env.now - self.last_ip > 40:
                    destination = '2001:3::1'
                    source = 'LBR'
                    self.network.send_message(self, self.node_id,
                                              Message("IP", {'destination': destination, 'source': source},
                                                      self.node_id))
                    self.last_ip = self.env.now
            if self.node_id == 2:
                if self.env.now - self.last_ip > 40:
                    destination = '2001::1'
                    source = self.ip_address
                    self.network.send_message(self, self.parent, Message("IP", {'destination': destination,'source': source}, self.node_id))
                    self.last_ip = self.env.now

            # Process incoming messages
            while self.inbox:
                message: Message = self.inbox.pop(0)
                match message.message_type:
                    case "ND":
                        self.network.send_message(self, message.sender_id, Message("ACK", None, self.node_id))
                        if message.sender_id not in self.neighbors.keys():
                            self.network.send_message(self, message.sender_id, Message("ND", None, self.node_id))
                    case "ACK":
                        self.neighbors[message.sender_id] = self.env.now
                    case "DIO":
                        if message.payload['instanceID'] > self.instanceID or (not self.grounded and message.payload['grounded']):
                            if not self.grounded:
                                if message.payload['grounded']:
                                    self.isLBR = False
                                    self.grounded = message.payload['grounded']
                                    self.dis_count = 0
                                    self.dis_interval = self.original_dis_interval


                            self.instanceID = message.payload['instanceID']
                            self.parent_candidates = {}
                            self.last_gr = 0
                            self.parent = None
                            self.rank = None
                            self.DAGrank = None
                        
                        if message.payload['ip_address'] is not None:
                            self.ip_address = message.payload['ip_address']
                            self.subnet = message.payload['subnet']
                            self.ip_prefix = message.payload['prefix']

                            if len(self.routing_table) > 0:
                                self.update_ip_routing_table()

                        elif self.DAGrank is None or self.DAGrank >= message.payload['DAGrank']:
                            # only add if it is not already on the list
                            if message.payload['rank'] is not None:
                                self.parent_candidates[message.sender_id] = self.objective_function(message.payload['rank'], self.network.get_connection_metrics(self.node_id, message.sender_id))

                            self.routing_table = {}
                            self.ip_routing_table = {}
                            self.subnet_routing_table = {}
                            if self.isLBR:
                                yield self.env.timeout(0.002)
                            else:
                                yield self.env.timeout(0.02)

                        yield self.env.timeout(0.02)
                    case "DAO":                       
                        if message.sender_id in self.parent_candidates.keys():
                            del self.parent_candidates[message.sender_id]
                        self.update_routing_table(message.payload['routing_table'], message.sender_id, False)

                        if self.parent is not None:
                            self.network.send_message(self, self.parent,
                                                      Message("DAO", {'routing_table': self.routing_table},
                                                              self.node_id))
                        if self.isLBR and len(self.routing_table) > 0:
                            self.received_DAO = True

                        if self.isLBR:
                            yield self.env.timeout(0.004)
                        else:
                            yield self.env.timeout(0.002)
                    case "DAO-ACK":
                        if message.sender_id in self.routing_table.values() and not message.payload['isChild']:
                            self.update_routing_table(message.payload['routing_table'], message.sender_id, True)
                    case "DIS":  # Optional
                        if self.grounded:
                            self.network.send_message(self, message.sender_id, Message("DIO", {'DAGrank': self.DAGrank,
                                                                                      'rank': self.rank,
                                                                                      'instanceID': self.instanceID,
                                                                                      'routing_table': self.routing_table,
                                                                                      'ip_address': None,
                                                                                      'subnet': None,
                                                                                      'prefix': None,
                                                                                      'grounded': self.grounded},
                                                                              self.node_id))
                        yield self.env.timeout(0.002)

                    case "HB":
                        self.neighbors[message.sender_id] = self.env.now

                    case "GR":
                        if self.isLBR:
                            self.instanceID += 1
                            self.routing_table = {}
                            self.ip_routing_table = {}
                            self.subnet_routing_table = {}
                            self.parent = None
                            self.parent_candidates = {}
                            self.ip_address = None
                            self.subnet = None
                            self.ip_prefix = None
                            for neighbor in self.neighbors.keys():
                                self.network.send_message(self, neighbor, Message("DIO", {'DAGrank': self.DAGrank,
                                                                                          'rank': self.rank,
                                                                                          'instanceID': self.instanceID,
                                                                                          'routing_table': self.routing_table,
                                                                                          'ip_address': None,
                                                                                          'subnet': None,
                                                                                          'prefix': None,
                                                                                          'grounded': self.grounded},
                                                                                  self.node_id))
                            self.last_dodag = self.env.now
                        else:
                            if message.payload['nr'] > self.last_gr:
                                self.grounded = False
                                self.routing_table = {}
                                self.ip_routing_table = {}
                                self.subnet_routing_table = {}
                                self.parent = None
                                self.parent_candidates = {}
                                self.ip_address = None
                                self.subnet = None
                                self.ip_prefix = None
                                self.rank = None
                                self.DAGrank = None

                                self.last_gr = message.payload['nr']
                                for neighbor in self.neighbors.keys():
                                    self.network.send_message(self, neighbor,
                                                              Message("GR", {'nr': message.payload['nr']},
                                                                      self.node_id))
                        if self.isLBR:
                            yield self.env.timeout(0.002)
                        else:
                            yield self.env.timeout(0.02)
                    case "IP":
                        if self.subnet is not None:
                            if self.ip_address == message.payload['destination']:
                                print(f"Node {self.node_id} Received IP message from {message.payload['source']}")
                            elif message.payload['destination'] in self.ip_routing_table.keys():
                                for ip_address in self.ip_routing_table.keys():
                                    if ip_address == message.payload['destination']:
                                        self.network.send_message(self, self.ip_routing_table[ip_address],
                                                                  Message("IP",
                                                                          {'destination': message.payload['destination'],
                                                                           'source': message.payload['source'], },
                                                                          self.node_id))
                            elif message.payload['destination'][0:len(self.subnet)] in self.subnet_routing_table.keys():
                                print(f"Destination: {message.payload['destination']} Prefix length {len(self.subnet)}")
                                for subnet in self.subnet_routing_table.keys():
                                    if subnet == message.payload['destination'][0:len(self.subnet)]:
                                        self.network.send_message(self,
                                                                  self.ip_routing_table[self.subnet_routing_table[subnet]],
                                                                  Message("IP",
                                                                          {'destination': message.payload['destination'],
                                                                           'source': message.payload['source'], },
                                                                          self.node_id))
                            elif self.parent is not None:
                                self.network.send_message(self, self.parent,
                                                          Message("IP", {'destination': message.payload['destination'],
                                                                         'source': message.payload['source'], },
                                                                  self.node_id))
                            else:
                                print(f"Address {message.payload['destination']} not in network")


            if not self.grounded and self.env.now - self.last_dis > self.dis_interval:
                #multiply dis_interval by a random number between 1 and 2
                self.dis_interval = self.dis_interval
                self.dis_count += 1
                for neighbor in self.neighbors.keys():
                    self.network.send_message(self, neighbor, Message("DIS", None, self.node_id))
                self.last_dis = self.env.now

            if self.received_DAO:
                self.update_ip_routing_table()
                self.received_DAO = False

            # Send heartbeat messages to neighbors
            if self.env.now - self.last_beat > self.heartbeat_interval:
                for neighbor in self.neighbors.keys():
                    self.network.send_message(self, neighbor, Message("HB", None, self.node_id))
                #Send a DAO to parent to inform them they are still their child
                self.network.send_message(self, self.parent,
                                        Message("DAO", {'routing_table': self.routing_table}, self.node_id))
                self.last_beat = self.env.now

            # Check if the parent should be updated (LBR has no parent)
            if not self.isLBR:
                old_parent = self.parent
                self.update_parent()
                if old_parent != self.parent or (old_parent is None and self.parent is not None):
                    # Inform old parent that node is no longer child
                    if old_parent is not None:
                        self.network.send_message(self, old_parent,
                                              Message("DAO-ACK", {'isChild': False, 'isParent': False, 'routing_table': self.routing_table}, self.node_id))
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
                                                               'subnet': None,
                                                               'prefix': None,
                                                               'grounded': self.grounded},
                                                              self.node_id))

            if self.dis_count > 3 and not self.isLBR and self.parent is None:
                self.isLBR = True
                print(f"Node {self.node_id} is now LBR I am root!")
                self.rank = 0
                self.DAGrank = 0
                self.dis_count = 0
                self.parent = None
                yield self.env.timeout(0.02)

            # Check if neighbors are still alive
            for node in list(self.neighbors.keys()):
                if self.env.now - self.neighbors[node] > self.heartbeat_interval * 2:
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
                    self.grounded = False
                    self.routing_table = {}
                    self.ip_routing_table = {}
                    self.subnet_routing_table = {}
                    self.parent_candidates = {}
                    self.ip_address = None
                    self.subnet = None
                    self.ip_prefix = None
                    self.inbox = []
                    self.rank = None
                    self.DAGrank = None
                    print(f"Node {self.node_id} sending GR")
                    for neighbor in self.neighbors.keys():
                        self.network.send_message(self, neighbor, Message("GR", {'nr': self.last_gr + 1}, self.node_id))
                else:
                    if self.log:
                        print(f"13: Node {self.node_id} sending DAO to parent {self.parent}")
                    self.network.send_message(self, self.parent,
                                              Message("DAO", {'routing_table': self.routing_table}, self.node_id))

            yield self.env.timeout(0.1)

    def update_routing_table(self, routing_table, sender_id, remove_child):
        keys_to_delete = []
        for key, value in self.routing_table.items():
            if value == sender_id:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            self.routing_table.pop(key)
        if not remove_child:
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
