import time
from generate_script import generate_script
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


def generate_frame(nodes, connections, duration, preserve_last=False, frame_text=None):
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
    :param frame_text: Optional text to display at the top of the frame
    :return: moviepy.ImageClip object
    """
    global _last_frame_state
    print("trying to generate one frame")
    # Create a directed graph for current nodes
    G = nx.DiGraph()
    
    # Add nodes with their labels
    current_node_indices = set()
    print("getting nodes in generate frame", nodes, connections)
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
    
    # Create figure for drawing with proper margins
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Add frame text at the top if provided with padding
    if frame_text:
        # Add text with word wrapping at 80 characters
        wrapped_text = '\n'.join([frame_text[i:i+80] for i in range(0, len(frame_text), 80)])
        fig.text(0.5, 0.96, wrapped_text, 
                ha='center', va='top', 
                fontsize=13, fontweight='bold',
                color='darkblue',
                bbox=dict(boxstyle='round,pad=0.8', facecolor='lightyellow', alpha=0.8, edgecolor='darkblue', linewidth=2))
        # Adjust subplot to leave space for text
        fig.subplots_adjust(top=0.88, bottom=0.05, left=0.05, right=0.95)
    else:
        # More space for graph when no text
        fig.subplots_adjust(top=0.95, bottom=0.05, left=0.05, right=0.95)
    
    ax.axis('off')
    # Set explicit limits to ensure margins
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    
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
        'star': '*',
        'box': 's'
    }
    
    # Calculate dynamic node sizes based on label length
    # Base size of 3000, plus 200 per character (minimum 3000, maximum 8000)
    node_sizes = {}
    for i, (shape, color, text) in enumerate(nodes):
        text_length = len(text)
        # Formula: base size + (characters * character_width)
        node_size = max(3000, min(8000, 2500 + text_length * 220))
        node_sizes[i] = node_size
    
    # Draw disappeared nodes (ghost nodes) if preserve_last is True
    if preserve_last and _last_frame_state['nodes'] is not None:
        previous_node_indices = set(range(len(_last_frame_state['nodes'])))
        disappeared_nodes = previous_node_indices - current_node_indices
        
        for i in disappeared_nodes:
            if i < len(_last_frame_state['nodes']) and i in pos:
                shape, color, text = _last_frame_state['nodes'][i]
                marker = shape_map.get(shape.lower(), 'o')
                ghost_size = 2500 + len(text) * 220  # Same formula as active nodes
                
                # Draw ghost node (semi-transparent, gray)
                nx.draw_networkx_nodes(
                    G, pos,
                    nodelist=[i],
                    node_color='lightgray',
                    node_shape=marker,
                    node_size=ghost_size,
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
    
    # Draw current nodes by shape and color with dynamic sizing
    for i, (shape, color, text) in enumerate(nodes):
        if i in G.nodes():
            marker = shape_map.get(shape.lower(), 'o')
            nx.draw_networkx_nodes(
                G, pos,
                nodelist=[i],
                node_color=color,
                node_shape=marker,
                node_size=node_sizes[i],
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
    
    # Draw labels for current nodes with better sizing
    labels = {i: node_data[2] for i, node_data in enumerate(nodes) if i in G.nodes()}
    
    # Draw labels with dynamic font size based on text length
    for i, label_text in labels.items():
        if i in pos:
            # Shorter labels = larger font, longer labels = smaller font
            font_size = max(8, min(12, 120 // max(1, len(label_text))))
            ax.text(pos[i][0], pos[i][1], label_text,
                   fontsize=font_size,
                   ha='center',
                   va='center',
                   color='white',
                   fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.3, edgecolor='none'))
    
    # Save the figure to a temporary file with proper margins
    temp_dir = tempfile.gettempdir()
    temp_image_path = os.path.join(temp_dir, f'graph_frame_{id(G)}.png')
    # Don't use tight_layout as we manually set subplots_adjust
    plt.savefig(temp_image_path, dpi=150, facecolor='white', bbox_inches=None)
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
    
    :param frames: List of frame specifications, each containing:
                   - (nodes, connections, duration) for basic frames
                   - (nodes, connections, duration, frame_text) for frames with text
    :param preserve_continuity: If True, maintains position continuity and shows ghost nodes between frames
    :return: moviepy.CompositeVideoClip or concatenated clip
    """
    # Reset state before generating new sequence
    if preserve_continuity:
        reset_frame_state()
    
    clips = []
    print("in get  generate frames", frames)
    for i, frame_data in enumerate(frames):

        print("in generate frames", i, frame_data)
        text, nodes, connections = frame_data['text'], frame_data['nodes'], frame_data['connections']
        # nodes = [tuple(el) for el in nodes]
        duration = 5 # hardcoded
        print("i", i, nodes, connections, duration)

        # First frame doesn't preserve (nothing to preserve from)
        # Subsequent frames preserve if preserve_continuity is enabled
        preserve_flag = preserve_continuity and i > 0
        clip = generate_frame(nodes, connections, duration, preserve_last=preserve_flag, frame_text=text)
        clips.append(clip)
    
    # Concatenate all clips
    final_clip = concatenate_videoclips(clips, method="compose")
    return final_clip


def generate_animated_frame_sequence(nodes, connections, frame_text=None, duration_per_step=1.0):
    """
    Generate a sequence of frames where connections appear one by one.
    Each step shows one more connection than the previous.
    
    :param nodes: List of node tuples [(shape, color, text), ...]
    :param connections: List of connection tuples [((source,), target), ...]
    :param frame_text: Text to display at top of all frames in sequence
    :param duration_per_step: Duration in seconds for each animation step
    :return: List of frame specifications for generate_frames()
    """
    if not connections:
        # No connections, just show all nodes
        return [(nodes, [], duration_per_step, frame_text)]
    
    frame_sequence = []
    
    # Build up connections progressively
    for i in range(len(connections)):
        current_connections = connections[:i+1]
        frame_sequence.append((nodes, current_connections, duration_per_step, frame_text))
    
    return frame_sequence


def generate_video_from_story(story_frames, duration_per_step=1.0, preserve_continuity=True):
    """
    Generate a video from a story sequence where each frame animates sequentially.
    
    :param story_frames: List of story frame dicts with format:
                        [{'text': '...', 'nodes': [[...]], 'connections': [...]}, ...]
    :param duration_per_step: Duration in seconds for each animation step
    :param preserve_continuity: If True, maintains position continuity between story frames
    :return: moviepy video clip
    """
    all_frames = []
    
    for story_frame in story_frames:
        nodes = [tuple(node) for node in story_frame['nodes']]  # Convert to tuples
        connections = story_frame['connections']
        text = story_frame.get('text', None)
        
        # Generate animated sequence for this story frame
        animated_sequence = generate_animated_frame_sequence(
            nodes, connections, text, duration_per_step
        )
        all_frames.extend(animated_sequence)
    
    # Generate the complete video
    return generate_frames(story_frames, preserve_continuity=preserve_continuity)


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
    frames = generate_script({"prompt": "Explain how the dijkstras algorithm works in detail."})
    print("all frames", frames)
    generated_clip = generate_video_from_story(frames)
    print("cliup is generated")

    generated_clip.write_videofile("testvideo.mp4", fps=30, audio=False)
    print("file saved")

    pass


def generate_audio(text):
    pass


# def main():
#     while True:
#         jobs = get_jobs()
#         for job in jobs:
#             engage_workers(job)
#
#         time.sleep(FETCH_INTERVAL_SECONDS)

engage_workers({})