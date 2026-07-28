import sys

from core.state import load_state
from core.utils import get_version
from engine.debug import archive_current_session_logs, register_close_handler
from engine.executor import execute
from engine.command_parser import parse
from engine.loader import load_renderers


def main():
    # Safety net: some Windows console codepages can't encode every
    # character the app might print. Never let that crash the app --
    # worst case a character shows oddly instead of raising.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except Exception:
                pass

    # Catches the console window being closed directly (X button), logoff,
    # or shutdown -- these don't raise a catchable Python exception, unlike
    # the exit/quit/EOF/Ctrl+C paths handled below in the loop itself.
    register_close_handler()

    load_renderers()

    state = load_state()

    print(f"// HSR PULL PLANNER v{get_version()} --  type 'help' for commands")

    try:
        while True:
            try:
                user_input = input("> ")
            except EOFError:
                # stdin closed unexpectedly (piped input ran out, stray Ctrl+Z) --
                # exit cleanly instead of crashing, same as typing 'exit'.
                break

            if user_input.lower() in ["exit", "quit"]:
                break

            command = parse(user_input)
            execute(state, command, raw_input=user_input)
    except KeyboardInterrupt:
        print()  # clean newline after ^C instead of a bare cursor jump
    finally:
        archive_current_session_logs()


if __name__ == "__main__":
    main()
