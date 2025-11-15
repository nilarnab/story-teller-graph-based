import time

FETCH_INTERVAL_SECONDS = 60


def get_jobs():
    return {}



def generate_frame(nodes, connections, duration, preserve_last=False):
    """

    :param nodes: of the form [(shape, color=black, text), ..]
    :param connections: of the form [((0, 2, 4), 3), ..] meaning, nodes 0, 2, 4 are connected to node 3
    :param duration: duration in second
    :param preserve_last: find out the nodes that are no longer required from the previous frame, delete those
    aniate addition of only the ones that are new.
    :return: moviepy.VideoFileClip (or something similar)
    """

def generate_frames(frames):
    """

    :param frames:
    :return:
    """
    frame = generate_frames()


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