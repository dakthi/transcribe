import matplotlib.pyplot as plt
import networkx as nx
from networkx.drawing.nx_agraph import to_agraph
from matplotlib.widgets import Button
from PIL import Image
import tempfile
import os

txt_file_path = "/Users/dakthi/Downloads/Organized/Folders/Folders/python-transcribe/transcribe/wbs.txt"

# Parse and also return levels for each node
def parse_numbered_list_to_edges(filepath):
    edges = []
    stack = []
    levels = {}  # Keep track of each node's depth

    with open(filepath, "r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip())
            content = line.strip()

            while stack and indent <= stack[-1][0]:
                stack.pop()

            parent = stack[-1][1] if stack else "Thi"
            edges.append((parent, content))
            level = len(stack) + 1
            levels[content] = level
            stack.append((indent, content))

    levels["Thi"] = 0
    return edges, levels

# Draw graph with leveled nodes and high-res rendering
def draw_graph(edges, levels, ax):
    ax.clear()

    G = nx.DiGraph()
    G.add_edges_from(edges)
    A = to_agraph(G)
    A.graph_attr.update(rankdir='TB', splines='ortho')

    # Group nodes by level to align them
    level_nodes = {}
    for node, lvl in levels.items():
        level_nodes.setdefault(lvl, []).append(node)

    for lvl, nodes in level_nodes.items():
        with A.subgraph() as s:
            s.graph_attr['rank'] = 'same'
            for n in nodes:
                s.add_node(n)

    # Node styles
    for node in A.nodes():
        node.attr.update({
            'shape': 'box',
            'style': 'filled,setlinewidth(2)',
            'fillcolor': 'white',
            'color': 'black',
            'fontname': 'Times-Roman',
            'fontsize': '10'
        })

    for edge in A.edges():
        edge.attr['color'] = 'black'

    # Render to high-res image
    with tempfile.NamedTemporaryFile(suffix='.png') as tmpfile:
        A.draw(tmpfile.name, prog='dot', format='png', args='-Gdpi=300')
        img = Image.open(tmpfile.name)
        ax.imshow(img)
        ax.axis('off')
        plt.tight_layout()
        plt.draw()

# Callback for refresh
def on_refresh(event):
    try:
        edges, levels = parse_numbered_list_to_edges(txt_file_path)
        draw_graph(edges, levels, ax)
    except Exception as e:
        print(f"Error: {e}")

# Set up layout
fig, ax = plt.subplots(figsize=(14, 10))
plt.subplots_adjust(bottom=0.2)

# Refresh button BELOW the image
refresh_ax = plt.axes([0.4, 0.05, 0.2, 0.05])
refresh_button = Button(refresh_ax, 'Refresh')
refresh_button.label.set_fontsize(10)
refresh_button.on_clicked(on_refresh)

# First render
on_refresh(None)
plt.show()
