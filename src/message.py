class Message:
    def __init__(self, message_type, payload, sender_id):
        self.message_type = message_type
        self.payload = payload
        self.sender_id = sender_id
