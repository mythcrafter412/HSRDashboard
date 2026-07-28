from engine.validator import validate
from engine.debug import trace

from engine.handlers import HANDLERS


# -----------------------------
# MAIN EXECUTOR (DISPATCH ONLY)
# -----------------------------
def execute(state, command, raw_input=None):

    if raw_input is not None:
        trace(state, "TRACE", "PARSER", f"raw input: {raw_input}")

    if command is None:
        if raw_input is not None:
            trace(state, "WARN", "PARSER", f"unrecognized: {raw_input}")
        return

    trace(state, "DEBUG", "EXECUTOR", f"received: {command}")

    # -------------------------
    # VALIDATION
    # -------------------------
    valid, msg = validate(command, state)

    if not valid:
        trace(state, "WARN", "EXECUTOR", f"VALIDATION FAILED: {msg}")
        print(f"[ERROR] {msg}")
        return

    action    = command.get("action")
    subdomain = command.get("subdomain")

    # -------------------------
    # ROUTE LOOKUP
    # -------------------------
    handler = HANDLERS.get((action, subdomain))

    if not handler:
        trace(state, "ERROR", "EXECUTOR", f"NO HANDLER FOR: {(action, subdomain)}")
        return

    # -------------------------
    # EXECUTE HANDLER
    # -------------------------
    handler(state, command)
