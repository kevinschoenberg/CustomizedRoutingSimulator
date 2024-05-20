class Connection:
    def __init__(self, node1, node2, delay=0, etx=1):
        self.node1 = node1
        self.node2 = node2
        self.delay = delay
        self.ETX = etx