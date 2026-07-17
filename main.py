from core.state import load_state
from engine.executor import execute
from engine.command_parser import parse
from engine.loader import load_renderers


def main():
    load_renderers()

    state = load_state()

    print("// HSR PULL PLANNER v0.1.1 —  type 'help' for commands")

    while True:
        user_input = input("> ")

        if user_input.lower() in ["exit", "quit"]:
            break

        command = parse(user_input)
        execute(state, command, raw_input=user_input)


if __name__ == "__main__":
    main()
