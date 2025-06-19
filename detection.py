import math
from at_switch_sim import session_stream  # simulated switch input
from pc_control import trigger_press

THRESHOLD = 0.3
FS = 10000
BLOCKSIZE = 100
DEBOUNCE_MS = 50
REFRACTORY = math.ceil(DEBOUNCE_MS * FS / (1000 * BLOCKSIZE))
print(f"Debounce cooldown is {REFRACTORY} blocks")


def run_detection(scanner):
    """Run the simple detection loop and forward events to the scanner."""
    cooldown = 0
    for block in session_stream(fs=FS, n_presses=10, blocksize=BLOCKSIZE, continuous=False):
        if cooldown:
            cooldown -= 1
            continue

        if max(abs(block)) > THRESHOLD:
            trigger_press(scanner)
            cooldown = REFRACTORY
