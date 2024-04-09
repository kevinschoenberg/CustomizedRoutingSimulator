import simpy

nodes = []

#TODO Message type class

class Node:
    def __init__(self, env, name, position, range, isLBR=False):
        self.env = env
        self.name = name
        self.position = position
        self.range = range
        self.inbox = []
        self.isLBR = isLBR
        self.action = env.process(self.run())

    def run(self):
        while True:
            if self.isLBR:
                self.broadcast('Hello from LBR ' + self.name)

            while self.inbox:
                message = self.inbox.pop(0)
                print(self.name + ' received: ' + message)

                #TODO Process message

            yield self.env.timeout(1)
    
    def broadcast(self, message):
        for node in nodes:
            if node != self and self.distance(node) <= self.range:
                node.inbox.append(message)

    def send_to(self, node, message):
        if self.distance(node) <= self.range:
            node.inbox.append(message)

    def distance(self, node):
        return ((self.position[0] - node.position[0])**2 + (self.position[1] - node.position[1])**2)**0.5


def main():

    env = simpy.Environment()
    node1 = Node(env, 'Node1', (0, 0), 4, True)
    node2 = Node(env, 'Node2', (1, 1), 5)
    node3 = Node(env, 'Node3', (2, 1), 1)
    nodes.append(node1)
    nodes.append(node2)
    nodes.append(node3)
    env.run(until=10)


if __name__ == "__main__":
    main()
