import importlib
import os


def load_renderers():
    base_path = os.path.join(os.path.dirname(__file__), "..", "rendering")

    for file in os.listdir(base_path):
        if file.endswith("_renderer.py"):
            module_name = f"rendering.{file[:-3]}"
            try:
                importlib.import_module(module_name)
            except Exception as e:
                print(f"[LOADER ERROR] {module_name}: {e}")
