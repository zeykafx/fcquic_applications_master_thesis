from ipaddress import IPv4Network


class BfdGlobal:
    def __init__(self):
        self.peers = None

    def set_peers(self, peers: list[str]):
        self.peers = peers

    def __str__(self):
        s = ""
        if self.peers is not None:
            s += f"bfd\n"
            for peer in self.peers:
                s += f"  peer {peer}\n  exit\n"
            s += f"exit"
        return s
