class IsisGlobal:
    def __init__(self):
        self.id = None

    def set_id(self, id):
        self.id = id

    def __str__(self):
        s = ""
        if self.id is not None:
            s += "router isis 1\n"
            s += "  is-type level-1\n"
            s += F"  net 49.0000.0000.0000.{str(self.id).zfill(4)}.00\n"
            s += "  lsp-timers level-1 gen-interval 5 refresh-interval 10 max-lifetime 1200\n"
            s += "  spf-interval 5\n"
            s += "exit"
        return s

class IsisInterface:
    def __init__(self):
        self.enabled = False
        self.enabled_bfd = False
        self.weight = None
        self.passive = None
        
    def enable(self, weight: int = 1):
        self.enabled = True
        self.weight = weight
    
    def set_passive(self):
        self.passive = True

    def enable_bfd(self):
        self.enabled_bfd = True

    def __str__(self):
        s = ""
        if self.enabled:
            s += "  ip router isis 1\n"
            s += "  isis network point-to-point\n"
            s += f"  isis metric {self.weight}\n"
        if self.enabled_bfd:
            s += "  isis bfd\n"
        if self.passive:
            s += "  isis passive\n"
        return s
