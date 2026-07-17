VIEW_REGISTRY = {}

def register_view(name, func):
    VIEW_REGISTRY[name] = func


def get_view(name):
    return VIEW_REGISTRY.get(name)
