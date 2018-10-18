import json

# Message objects
class Message:
    DEFAULT_TTL = 128

    def __init__(self, mtype, src, dst, params):
        self.source = src
        self.destination = dst
        self.type = mtype

        if 'ttl' in params:
            ttl = params['ttl']
        else:
            ttl = Message.DEFAULT_TTL

        if mtype == 'data':
            self.payload = params['payload']
            self.ttl = ttl
        elif mtype == 'update':
            self.distances = params['distances']
            self.ttl = None
        elif mtype == 'trace':
            self.hops = params['hops']
            self.ttl = ttl

    def __str__(self):
        skeleton = {
            'source': self.source,
            'destination': self.destination,
            'type': self.type
        }

        extra = {}
        if self.type == 'data':
            extra['payload'] = self.payload
            if self.ttl is not None:
                extra['ttl'] = self.ttl
        elif self.type == 'update':
            extra['distances'] = self.distances
        elif self.type == 'trace':
            extra['hops'] = self.hops
            if self.ttl is not None:
                extra['ttl'] = self.ttl

        skeleton.update(extra)
        return json.dumps(skeleton)
