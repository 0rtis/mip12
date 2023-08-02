class Storage:
    """
    A key-value database. ETH Go uses LevelDB
    """
    def __init__(self):
        self.db = {}

    def read(self, key) -> bytes:
        if key not in self.db:
            return bytes(0)
        return self.db[key]

    def write(self, key, value):
        self.db[key] = value
