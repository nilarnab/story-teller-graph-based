import time
from collections import defaultdict

from dotenv import load_dotenv

from generate_script import generate_script
import networkx as nx
import matplotlib.pyplot as plt
from moviepy import ImageClip, concatenate_videoclips
import os
import tempfile

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from moviepy import AudioFileClip

