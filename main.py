import time
import networkx as nx
import matplotlib.pyplot as plt
from moviepy import ImageClip, concatenate_videoclips
import os
import tempfile

FETCH_INTERVAL_SECONDS = 60

# Global state to preserve layout and previous frame information
_last_frame_state = {
    'positions': None,
    'nodes': None,
    'graph': None,
    'next_position_index': 0  # Track position for new nodes
}

# Predefined positions for nodes (circular layout around center)
def _get_predefined_position(index):
    """
    Get a predefined position for a node based on its index.
    Positions are arranged in concentric circular layers starting from center.
    
    - Node 0: Center (0.5, 0.5)
    - Nodes 1-6: First layer (6 nodes in circle around center)
    - Nodes 7-12: Second layer (6 nodes in circle farther out)
    - And so on...
    
    All positions are guaranteed to be within bounds (0, 1).
    Positions are deterministic based on node index only.
    
    :param index: Node index (0 is center, 1+ are in layers)
    :return: (x, y) position tuple with values in [0, 1]
    """
    import math
    
    if index == 0:
        # First node at center
        return (0.5, 0.5)
    
    # Determine which layer this node belongs to
    # Layer 1 has nodes 1-6 (6 nodes)
    # Layer 2 has nodes 7-18 (12 nodes)
    # Layer k has nodes with 6*k positions
    layer = 1
    nodes_before_layer = 1  # Node 0 is at center
    nodes_in_current_layer = 6
    
    # Find which layer the node is in
    while nodes_before_layer + nodes_in_current_layer <= index:
        nodes_before_layer += nodes_in_current_layer
        layer += 1
        nodes_in_current_layer = 6 * layer
    
    # Position within the current layer (0-indexed)
    position_in_layer = index - nodes_before_layer
    
    # Calculate angle for this position in the layer
    angle = (2 * math.pi * position_in_layer) / nodes_in_current_layer
    
    # Calculate radius based on layer (each layer gets progressively larger)
    # Layer 1: radius 0.18, Layer 2: radius 0.32, etc.
    # Keep radius small enough to fit in [0, 1] bounds
    radius = 0.15 + (layer - 1) * 0.12
    radius = min(radius, 0.35)  # Cap at 0.35 to stay within bounds
    
    # Calculate position using polar coordinates
    x = 0.5 + radius * math.cos(angle)
    y = 0.5 + radius * math.sin(angle)
    
    # Ensure position is within bounds [0, 1]
    x = max(0.05, min(0.95, x))
    y = max(0.05, min(0.95, y))
    
    return (x, y)


def get_jobs():
    return {}


def reset_frame_state():
    """
    Reset the global frame state. Call this when starting a new video sequence.
    """
    global _last_frame_state
    # IMPORTANT: Clear the existing dict instead of reassigning!
    # This ensures all imports continue to reference the same object
    _last_frame_state.clear()
    _last_frame_state.update({
        'positions': None,
        'nodes': None,
        'graph': None,
        'next_position_index': 0
    })


def generate_frame(nodes, connections, duration, preserve_last=False):
    """
    Generate a video frame showing a directed graph with specified nodes and connections.
    
    :param nodes: List of tuples of the form [(shape, color, text), ..]
                  shape: 'circle', 'square', 'triangle', 'diamond', etc.
                  color: color name or hex code (e.g., 'red', '#FF5733')
                  text: label text for the node
    :param connections: List of tuples of the form [((0, 2, 4), 3), ..]
                        meaning nodes 0, 2, 4 are connected to node 3
    :param duration: Duration in seconds for the video clip
    :param preserve_last: If True, preserve node positions from previous frame and show 
                         disappeared nodes as ghost nodes (faded/transparent)
    :return: moviepy.ImageClip object
    """
    global _last_frame_state
    
    # Create a directed graph for current nodes
    G = nx.DiGraph()
    
    # Add nodes with their labels
    current_node_indices = set()
    for i, (shape, color, text) in enumerate(nodes):
        G.add_node(i, shape=shape, color=color, text=text)
        current_node_indices.add(i)
    
    # Add edges based on connections
    for source_nodes, target_node in connections:
        if isinstance(source_nodes, (list, tuple)):
            for source_node in source_nodes:
                G.add_edge(source_node, target_node)
        else:
            G.add_edge(source_nodes, target_node)
    
    # Create figure for drawing
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis('off')
    
    # Determine node positioning with fixed positions
    pos = {}
    
    # ALWAYS use previous positions as base if available
    if _last_frame_state['positions'] is not None:
        pos = _last_frame_state['positions'].copy()
    
    # Assign positions to all nodes (new and existing)
    for i in range(len(nodes)):
        if i not in pos:
            # Assign predefined position for new nodes
            pos[i] = _get_predefined_position(i)
    
    # Also preserve positions for ghost nodes (if preserve_last is enabled)
    if preserve_last and _last_frame_state['positions'] is not None:
        for idx in _last_frame_state['positions']:
            if idx not in pos:
                pos[idx] = _last_frame_state['positions'][idx]
    
    # Shape marker mapping
    shape_map = {
        'circle': 'o',
        'square': 's',
        'triangle': '^',
        'diamond': 'D',
        'pentagon': 'p',
        'hexagon': 'h',
        'star': '*'
    }
    
    # Draw disappeared nodes (ghost nodes) if preserve_last is True
    if preserve_last and _last_frame_state['nodes'] is not None:
        previous_node_indices = set(range(len(_last_frame_state['nodes'])))
        disappeared_nodes = previous_node_indices - current_node_indices
        
        for i in disappeared_nodes:
            if i < len(_last_frame_state['nodes']) and i in pos:
                shape, color, text = _last_frame_state['nodes'][i]
                marker = shape_map.get(shape.lower(), 'o')
                
                # Draw ghost node (semi-transparent, gray)
                nx.draw_networkx_nodes(
                    G, pos,
                    nodelist=[i],
                    node_color='lightgray',
                    node_shape=marker,
                    node_size=2000,
                    alpha=0.3,
                    ax=ax
                )
                
                # Draw ghost label with strikethrough effect
                if i in pos:
                    ax.text(pos[i][0], pos[i][1], f'({text})',
                           fontsize=8,
                           ha='center',
                           va='center',
                           color='gray',
                           alpha=0.5,
                           style='italic')
    
    # Draw current nodes by shape and color
    for i, (shape, color, text) in enumerate(nodes):
        if i in G.nodes():
            marker = shape_map.get(shape.lower(), 'o')
            nx.draw_networkx_nodes(
                G, pos,
                nodelist=[i],
                node_color=color,
                node_shape=marker,
                node_size=2000,
                ax=ax
            )
    
    # Draw edges
    nx.draw_networkx_edges(
        G, pos,
        edge_color='gray',
        arrows=True,
        arrowsize=20,
        arrowstyle='->',
        width=2,
        ax=ax
    )
    
    # Draw labels for current nodes
    labels = {i: node_data[2] for i, node_data in enumerate(nodes) if i in G.nodes()}
    nx.draw_networkx_labels(
        G, pos,
        labels,
        font_size=10,
        font_weight='bold',
        font_color='white',
        ax=ax
    )
    
    # Save the figure to a temporary file
    temp_dir = tempfile.gettempdir()
    temp_image_path = os.path.join(temp_dir, f'graph_frame_{id(G)}.png')
    plt.tight_layout()
    plt.savefig(temp_image_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    
    # Create video clip from the image
    clip = ImageClip(temp_image_path, duration=duration)
    
    # ALWAYS update positions for next frame (whether preserve_last is True or not)
    # This ensures positions are available for subsequent frames
    _last_frame_state['positions'] = pos
    _last_frame_state['nodes'] = nodes
    _last_frame_state['graph'] = G
    
    # Clean up temporary file (optional, uncomment if you want immediate cleanup)
    # os.remove(temp_image_path)
    
    return clip

def generate_frames(frames, preserve_continuity=True):
    """
    Generate multiple frames and concatenate them into a single video.
    
    :param frames: List of frame specifications, each containing (nodes, connections, duration)
    :param preserve_continuity: If True, maintains position continuity and shows ghost nodes between frames
    :return: moviepy.CompositeVideoClip or concatenated clip
    """
    # Reset state before generating new sequence
    if preserve_continuity:
        reset_frame_state()
    
    clips = []
    for i, frame_data in enumerate(frames):
        nodes, connections, duration = frame_data
        # First frame doesn't preserve (nothing to preserve from)
        # Subsequent frames preserve if preserve_continuity is enabled
        preserve_flag = preserve_continuity and i > 0
        clip = generate_frame(nodes, connections, duration, preserve_last=preserve_flag)
        clips.append(clip)
    
    # Concatenate all clips
    final_clip = concatenate_videoclips(clips, method="compose")
    return final_clip


def engage_workers(job):
    """
    job structure expected

    {
    prompt [str]: some prmopt,
    file_path [None: str]: url of the file path,
    file_type [None: str]
    }

    :param job:
    :return:
    """
    pass

def main():
    while True:
        jobs = get_jobs()
        for job in jobs:
            engage_workers(job)

        time.sleep(FETCH_INTERVAL_SECONDS)