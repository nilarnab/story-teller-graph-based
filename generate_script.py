import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPEN_ROUTER_API_KEY"),
)

def get_raw_output(prompt):
    # First API call with reasoning
    response = client.chat.completions.create(
        # model="openai/gpt-5.1",
        model="openai/gpt-oss-20b:free",
        messages=[
            {
                "role": "user",
                "content": f"you will generate encodings for a video animations. "
                           f"the video to properly explain and teach the topic: '{prompt}' for the video "
                           "enccoding, we have multiple options: so mostly you create videos with multiple "
                           "frames each frame will have graph containing some boxes and some connections. so you define multiple frames to "
                           "explain the topic for each frame, you give a dialouge, and the visualisation of that dialogue. "
                           "in the visualisation, you mention boxes with names and ten draw connections. "
                           "you give the output as frame1? 'In a suppply change, there are multiople components connected together. "
                           "they flow from one point to the ohter. for example ccar can have multiple supply ch ain components' "
                           "visualisation: nodes: [(box, black, "
                           "basisc frame), (box, black, wheels), (box, black, car)] connections: (1, 2), (2, 3)."
                           "STRICTLY FOLLOW THE OUTPUT MODE: frame_number?frame_text?nodes details?connection details, where"
                           "node details must follow, shape1:color1:label1,shape2:color2:label2 and connection detail"
                           "must follow: node_index1,node_index2,...:node_index_k, to mean node_index1, node_index2 .. points to node_index_k. For multiple connection"
                           "texts, use the delimiter ';' in between. Make it like a story and use descriptive frame_text to make"
                           "the user understand the concept. A sample connection text miight look like node1,node2:node3;node2:node3;node3:node4 to mean"
                           "node1 and node2 points to node3, node2 points to node3 and node3 points to node4. Use dilimiter '$' between"
                           "the frames. Do not use next line as the delimiter. For frames which do not need a graph, make it as frame1?frametext1?NO_NODE?NO_NODE, as in mention NO_NODE in place of the graph details."
                           "YOU CANNOT USE SPECIAL CHARACTERS IN frame_text. DO NOT USE SPECIAL CHARACTER IN FRAME TEXT. Make atleast"
                           "8 frames to explain the concept clearly. For example"
                           "a full output might look something like:"
                           "frame1?frametext1?NO_NODE?NO_NODE$frame2?frametext2?shape1:color1:label1,shape2:color2:label2,shape3:color3:label3?0,1:2;2:1"
            }
        ],
        extra_body={"reasoning": {"enabled": True}}
    )

    # Extract the assistant message with reasoning_details
    response = response.choices[0].message

    return response.content

def parse_output(raw_output):
    frames = []
    for frame_text in raw_output.split("$"):
        text = None
        nodes = []
        connections = []

        frame_segments = frame_text.split("?")
        text = frame_segments[1]
        node_text_raw = frame_segments[2]
        connection_text_raw = frame_segments[3]

        if node_text_raw != "NO_NODE":
            for node_text in node_text_raw.split(","):
                node_tuple = node_text.split(":")
                nodes.append(node_tuple)

            for con_text in connection_text_raw.split(";"):
                conn_text_parsed = con_text.split(":")
                start_nodes = tuple([int(el) for el in conn_text_parsed[0].split(',')])
                end_node = int(conn_text_parsed[1])
                connections.append((start_nodes, end_node))

            frames.append({"text": text, "nodes": nodes, "connections": connections})

    return frames


def generate_script(job):
    """
        job structure expected

        {
        prompt [str]: some prmopt,
        file_path [None: str]: url of the file path, # phase 2
        file_type [None: str] # phase 2
        }
        :param job:

        :return:
        [{nodes: [(shape1, color1, text1), ...], connections: [((0, 2, 4), 3), ..]}], preserve_last: True}, ...]
        """

    prompt = job['prompt']
    # file_path = job['file_path']
    # file_type = job['file_type']

    raw_output = get_raw_output(prompt)
    parsed_output = parse_output(raw_output)

    return parsed_output


output = generate_script({"prompt": "Explain how the dijkstras algorithm works in detail."})
print(output)