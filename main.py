import time
from collections import defaultdict

from generate_script import generate_script
import networkx as nx
import matplotlib.pyplot as plt
from moviepy import ImageClip, concatenate_videoclips
import os
import tempfile
import textwrap

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from moviepy import AudioFileClip
from backend  import db
from moviepy import CompositeAudioClip


FETCH_INTERVAL_SECONDS = 60

load_dotenv()

elevenlabs = ElevenLabs(
  api_key=os.getenv("ELEVEN_LABS_KEY"),
)

# Global state to preserve layout and previous frame information
_last_frame_state = {
    'positions': None,
    'nodes': None,
    'graph': None,
    'next_position_index': 0  # Track position for new nodes
}


def generate_background_music(prompt):
#      lets use a pregenreated one for now
    audio_background_clip = AudioFileClip("75985_Study_Flow_2025-11-16T035030.mp3")
    return audio_background_clip


def get_audio(text):
    audio_stream = elevenlabs.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    temp_dir = tempfile.gettempdir()
    audio_path = f"tts_{int(time.time() * 1000)}.mp3"

    # IMPORTANT: iterate through the stream, do NOT do f.write(audio_stream)
    with open(audio_path, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)

    # Now load as MoviePy AudioFileClip
    audio_clip = AudioFileClip(audio_path)

    return audio_clip

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
    # Increased spacing: Layer 1: radius 0.20, Layer 2: radius 0.35, etc.
    # More spacing to prevent node overlap
    radius = 0.20 + (layer - 1) * 0.15
    radius = min(radius, 0.42)  # Cap at 0.42 to stay within bounds with margin
    
    # Calculate position using polar coordinates
    x = 0.5 + radius * math.cos(angle)
    y = 0.5 + radius * math.sin(angle)
    
    # Ensure position is within bounds [0, 1]
    x = max(0.05, min(0.95, x))
    y = max(0.05, min(0.95, y))
    
    return (x, y)


def get_jobs():
    jobs = db.get_all_new_jobs()
    return jobs


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


def generate_frame(nodes, connections, duration, preserve_last=False, frame_text=None, visible_nodes=None):
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
    :param visible_nodes: Set of node indices that should be visible. If None, all nodes are visible.
    :return: moviepy.ImageClip object
    """
    global _last_frame_state
    
    # Handle case with no nodes - display only text
    if not nodes or len(nodes) == 0:
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.axis('off')
        
        if frame_text:
            # Add text at center with word wrapping at 60 characters for better readability
            wrapped_text = textwrap.fill(frame_text, width=60)
            fig.text(0.5, 0.5, wrapped_text, 
                    ha='center', va='center', 
                    fontsize=24, 
                    color='black')
        
        # Save the figure to a temporary file
        temp_dir = tempfile.gettempdir()
        temp_image_path = os.path.join(temp_dir, f'text_frame_{int(time.time() * 1000)}.png')
        plt.savefig(temp_image_path, dpi=150, facecolor='white', bbox_inches=None)
        plt.close(fig)
        
        # Create video clip from the image
        clip = ImageClip(temp_image_path, duration=duration)
        return clip
    
    # print("trying to generate one frame")
    # Create a directed graph for current nodes
    G = nx.DiGraph()
    
    # If visible_nodes not specified, show all nodes
    if visible_nodes is None:
        visible_nodes = set(range(len(nodes)))
    
    # Add nodes with their labels
    current_node_indices = set()
    # print("getting nodes in generate frame", nodes, connections, "visible:", visible_nodes)
    for i, (shape, color, text) in enumerate(nodes):
        if i in visible_nodes:  # Only add visible nodes
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
        # Add text with word wrapping at 60 characters for consistency with text-only frames
        wrapped_text = textwrap.fill(frame_text, width=60)
        fig.text(0.5, 0.88, wrapped_text, 
                ha='center', va='top', 
                fontsize=24, 
                color='black')
        # Adjust subplot to leave more space for larger text
        fig.subplots_adjust(top=0.8, bottom=0.05, left=0.05, right=0.95)
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
        edge_color='black',
        arrows=True,
        arrowsize=100,
        arrowstyle='-|>',
        width=3,
        connectionstyle='arc3,rad=0.1',
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

    print("lenght fo frames", len(frames))
    # print("in get  generate frames", frames)
    clip_groups = defaultdict(list)

    for i, frame_data in enumerate(frames):

        # print("in generate frames", i, frame_data)
        ind, text, nodes, connections = frame_data['ind'], frame_data['text'], frame_data['nodes'], frame_data['connections']
        # Use duration from frame_data if provided, otherwise default to 5 seconds



        duration = frame_data.get('duration', 5)
        # Get visible nodes if specified
        visible_nodes = frame_data.get('visible_nodes', None)
        # print("i", i, nodes, connections, duration, "visible:", visible_nodes)

        # First frame doesn't preserve (nothing to preserve from)
        # Subsequent frames preserve if preserve_continuity is enabled
        preserve_flag = preserve_continuity and i > 0
        clip = generate_frame(nodes, connections, duration, preserve_last=preserve_flag, 
                             frame_text=text, visible_nodes=visible_nodes)
        clip_groups[(ind, text)].append(clip)

    clips = []
    print("lenght fo frames", len(clip_groups))
    for clips_group_key in clip_groups:
        clips_group = clip_groups[clips_group_key]
        id = clips_group_key[0]
        text = clips_group_key[1]
        frame_clip = concatenate_videoclips(clips_group, method="compose")

        audio_clip = get_audio(text)
        # how to set frame clip lenght to max frame_clip_length and audio_clip length

        video_duration = frame_clip.duration
        audio_duration = audio_clip.duration

        if audio_duration > video_duration:
            # extend video by freezing the last frame
            last_frame = frame_clip.get_frame(video_duration - 0.01)

            freeze_clip = ImageClip(last_frame).with_duration(audio_duration - video_duration)

            # concatenate original + freeze
            frame_clip = concatenate_videoclips([frame_clip, freeze_clip], method="compose")

        frame_clip = frame_clip.with_audio(audio_clip)

        clips.append(frame_clip)

    print("lenght fo frames", len(clips))

    # Concatenate all clips
    final_clip = concatenate_videoclips(clips, method="compose")
    background_music = generate_background_music("fast beat music, something good for study, lofi")

    video_duration = final_clip.duration
    background_music = background_music.subclipped(0, video_duration)

    # Optionally, lower the background music volume
    # background_music = background_music.volumex(0.3)  # 30% volume
    # Combine original audio and background music
    combined_audio = CompositeAudioClip([final_clip.audio, background_music.with_duration(final_clip.duration)])

    # Assign combined audio back to final_clip
    final_clip = final_clip.with_audio(combined_audio)

    return final_clip


def generate_animated_frame_sequence(nodes, connections, frame_text=None, duration_per_step=1.0):
    """
    Generate a sequence of frames where nodes and connections appear one by one.
    Nodes appear sequentially first, then the connection appears.
    
    :param nodes: List of node tuples [(shape, color, text), ...]
    :param connections: List of connection tuples [((source,), target), ...]
    :param frame_text: Text to display at top of all frames in sequence
    :param duration_per_step: Duration in seconds for each animation step
    :return: List of frame specifications for generate_frames()
    """
    if not connections:
        # No connections, show nodes appearing one by one
        frame_sequence = []
        if len(nodes) == 0:
            # Text-only frame - create a single frame with no visible nodes
            frame_sequence.append((nodes, [], duration_per_step, frame_text, set()))
        else:
            # Show nodes appearing one by one
            for i in range(len(nodes)):
                visible_nodes = set(range(i + 1))
                frame_sequence.append((nodes, [], duration_per_step, frame_text, visible_nodes))
        return frame_sequence
    
    frame_sequence = []
    
    # Track which nodes have been revealed
    visible_nodes = set()
    
    # Build up connections progressively, revealing nodes as they're connected
    for i in range(len(connections)):
        conn = connections[i]
        source_nodes, target_node = conn
        
        # Collect all nodes involved in this connection
        new_nodes = set()
        if isinstance(source_nodes, (list, tuple)):
            new_nodes.update(source_nodes)
        else:
            new_nodes.add(source_nodes)
        new_nodes.add(target_node)
        
        # Find nodes that haven't been shown yet
        nodes_to_reveal = new_nodes - visible_nodes
        
        # Show each new node appearing one at a time (without connection yet)
        for node_idx in sorted(nodes_to_reveal):
            visible_nodes.add(node_idx)
            # Show node without the new connection
            frame_sequence.append((nodes, connections[:i], duration_per_step, frame_text, visible_nodes.copy()))
        
        # Now show the connection (all nodes already visible)
        current_connections = connections[:i+1]
        frame_sequence.append((nodes, current_connections, duration_per_step, frame_text, visible_nodes.copy()))
    
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
    ind = 0
    for story_frame in story_frames:

        nodes = [tuple(node) for node in story_frame['nodes']]  # Convert to tuples
        connections = story_frame['connections']
        text = story_frame.get('text', None)
        
        # Generate animated sequence for this story frame
        animated_sequence = generate_animated_frame_sequence(
            nodes, connections, text, duration_per_step
        )
        for el in animated_sequence:
            all_frames.append((ind, el))
        # all_frames.extend(animated_sequence)
        ind += 1
    
    # Convert all_frames to the dict format expected by generate_frames
    formatted_frames = []
    for frame in all_frames:
        ind = frame[0]
        nodes, connections, duration, frame_text, visible_nodes = frame[1]
        formatted_frames.append({
            'ind': ind,
            'text': frame_text,
            'nodes': nodes,
            'connections': connections,
            'duration': duration,
            'visible_nodes': visible_nodes
        })
    
    # Generate the complete video with formatted frames
    return generate_frames(formatted_frames, preserve_continuity=preserve_continuity)


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
    frames = generate_script(job)
    print("all frames", len(frames), frames)
    generated_clip = generate_video_from_story(frames)
    print("cliup is generated")

    file_path = "testvideo.mp4"
    generated_clip.write_videofile(file_path, fps=20, audio_codec='aac')
    print("file saved")
    abs_file_path = os.path.abspath(file_path)

    return abs_file_path


def generate_audio(text):
    pass


def main(prompt, file_path):
    job = {"prompt": prompt, "file_path": file_path}
    print("main got job", job)
    file_path = engage_workers(job)
    print("main giving file path", file_path)
    return "dummy descrption", file_path, "dumm subheading"


# def main():
#     while True:
#         jobs = get_jobs()
#         print("jobs", jobs)
#         prompt = jobs['prompt_text']
#         filepath = jobs['file_path']
#
#         for job in jobs:
#             engage_workers(job)
#
#         time.sleep(FETCH_INTERVAL_SECONDS)

# engage_workers({})
# main()