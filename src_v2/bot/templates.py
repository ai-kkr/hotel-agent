from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_root = Path(__file__).parent

env = Environment(loader=FileSystemLoader(_root / "templates"), autoescape=True)

GREETING_TPL = env.get_template("greeting.md.j2")
