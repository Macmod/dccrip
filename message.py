import json

# Message objects
class Message:
    def __init__(self, mtype, src, dst, params):
        self.source = src
        self.destination = dst
        self.type = mtype

        if mtype == 'data':
            self.payload = params['payload']
        elif mtype == 'update':
            self.distances = params['distances']
        elif mtype == 'trace':
            self.hops = params['hops']

    def __str__(self):
        skeleton = {
            'source': self.source,
            'destination': self.destination,
            'type': self.type
        }

        extra = {}
        if self.type == 'data':
            extra['payload'] = self.payload
        elif self.type == 'update':
            extra['distances'] = self.distances
        elif self.type == 'trace':
            extra['hops'] = self.hops

        skeleton.update(extra)
        return json.dumps(skeleton)
