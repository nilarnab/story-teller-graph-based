from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

# First API call with reasoning
response = client.chat.completions.create(
  model="openai/gpt-5.1",
  messages=[
          {
            "role": "user",
            "content": "you will generate encodings for a video animations. "
                           "the video animaino is about the topic: 'how supply chain works' for the video "
                           "enccoding, we have multiple options: so mostly you create videos wiht multiple "
                           "frames each frame will have graph containing some boxes and some connections. so you define multiple frames to "
                           "explain the topic for each frame, you give a dialouge, and the visualisation of that dialogue. "
                           "in the visualisation, you mention boxes with names and ten draw connections. "
                           "you give the output as frame1: 'In a suppply change, there are multiople comoponents connected together. "
                           "they flow from one point to the ohter. for example ccar can have multiple supply ch ain components' "
                           "visualisation: nodes: [(box, black, basisc frame), (box, black, wheels), (box, black, car)] connections: (1, 2), (2, 3)."
                           "STRICTLY FOLLOW THE OUTPUT MODE: frame_number?frame_text?nodes details?connection details, where"
                           "node details must follow, shape1:color1:label1,shape2:color2:label2 and connection detail"
                           "must follow: node_index1,node_index2,...:node_index_k, to mean node_index1, node_index2 .. points to node_index_k. For multiple connection"
                           "texts, use the delimiter ';' in between. So a sample connection text miight look like node1,node2:node3;node2:node3;node3:node4 to mean"
                           "node1 and node2 points to node3, node2 points to node3 and node3 points to node4. Use dilimiter '$' between"
                           "the frames. Do not use next line as the delimiter. For frames which do not need a graph, make it as frame1:frametext1?NO_NODE?NO_NODE, as in mention NO_NODE in place of the graph details."
                           "YOU CANNOT USE SPECIAL CHARACTERS IN frame_text. DO NOT USE SPECIAL CHARACTER IN FRAME TEXT. For example"
                           "a full output might look something like:"
                           "frame1?frametext1?NO_NODE?NO_NODE$frame2?frametext2?shape1:color1:label1,shape2:color2:label2,shape3:color3:label3?0,1:2;2:1"
          }
        ],
  extra_body={"reasoning": {"enabled": True}}
)

# Extract the assistant message with reasoning_details
response = response.choices[0].message

print(response.content)