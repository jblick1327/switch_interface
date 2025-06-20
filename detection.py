from typing import Callable


def listen(callback: Callable[[], None]) -> None:
    """Very simple switch detection placeholder.

    This waits for the user to press Enter on stdin and calls ``callback``
    each time. Replace the body of this function with real audio-based
    detection logic when available.
    """
    try:
        while True:
            input("Press Enter to activate the switch...\n")
            callback()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    import math
    from at_switch_sim import session_stream  # simulated test module in gitignore for now
    # from audio_io...

    THRESHOLD = 0.3
    FS = 10000
    BLOCKSIZE = 100
    DEBOUNCE_MS = 50
    REFRACTORY = math.ceil(DEBOUNCE_MS * FS / (1000 * BLOCKSIZE))
    print(f"Debounce cooldown is {REFRACTORY} blocks")

    cooldown = 0
    debug_count = 0

    # currently only press_on logic
    for block in session_stream(fs=FS,
                                n_presses=10,
                                blocksize=BLOCKSIZE,
                                continuous=False):

        if cooldown:
            cooldown -= 1
            continue

        if max(abs(block)) > THRESHOLD:
            # press
            debug_count += 1
            cooldown = REFRACTORY

    print(debug_count)
