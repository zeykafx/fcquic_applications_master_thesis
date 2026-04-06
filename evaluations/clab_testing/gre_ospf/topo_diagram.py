from graphviz import Graph


g = Graph("GRE OSPF Topology", format="png")
g.attr(rankdir="LR", fontname="Helvetica", bgcolor="white", pad="0.5", nodesep="0.8", ranksep="1.2")
g.attr("node", fontname="Helvetica", fontsize="11", style="filled", color="#333333")
g.attr("edge", fontname="Helvetica", fontsize="9", color="#555555")

# router
g.node("spirou", "Spirou\n(Router)\nlo: 10.10.10.1", fillcolor="#ffcc00", shape="cylinder", height="0.8")
g.node("ecotype1", "Ecotype1\n(Router)\nlo: 10.10.10.2", fillcolor="#ffcc00", shape="cylinder", height="0.8")
g.node("ecotype2", "Ecotype2\n(Router)\nlo: 10.10.10.3", fillcolor="#ffcc00", shape="cylinder", height="0.8")

# hosts
g.node("pc1", "PC1\n10.10.11.2", fillcolor="#e2d9f3", shape="box")
g.node("pc2", "PC2\n10.10.12.2", fillcolor="#e2d9f3", shape="box")
g.node("pc3", "PC3\n10.10.13.2", fillcolor="#e2d9f3", shape="box")

# physical connection between spirou and ecotype1
g.edge("spirou", "ecotype1", 
       label="eth0\n10.100.1.0/24\n(no OSPF)", 
       style="solid", color="#888888")

# GRE tunnel with ospf enabled
g.edge("spirou", "ecotype1", 
       label="gre1 (Tunnel)\n192.168.1.0/24\nOSPF area 0", 
       style="dashed", color="#cc0000", penwidth="2")

g.edge("ecotype1", "ecotype2", 
       label="eth1\n10.10.2.0/24\nOSPF area 0", 
       color="#009933", penwidth="2")


g.edge("pc1", "spirou", label="eth1\n10.10.11.0/24")
g.edge("pc2", "ecotype1", label="eth2\n10.10.12.0/24")
g.edge("pc3", "ecotype2", label="eth2\n10.10.13.0/24")

g.attr(dpi="300")
out_name="gre_ospf_topology"
g.render(out_name, cleanup=True)
print(f"Diagram saved to {out_name}.png")
