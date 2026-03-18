"""Task template system — pre-built configurations for common workflows."""

import yaml
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class TaskTemplate:
    name: str
    description: str
    default_pipeline: str = "default"
    default_roles: dict = field(default_factory=dict)
    expected_duration_minutes: int = 60
    estimated_cost: float = 0.0
    parameters: list = field(default_factory=list)


class TemplateRegistry:
    def __init__(self, templates_dir=None):
        self.templates = {}
        if templates_dir:
            self.load_from_directory(templates_dir)

    def load_from_directory(self, templates_dir):
        path = Path(templates_dir)
        if not path.exists():
            return
        for f in path.glob("*.yaml"):
            with open(f) as fh:
                data = yaml.safe_load(fh)
            if data:
                tmpl = TaskTemplate(
                    name=data.get("name", f.stem),
                    description=data.get("description", ""),
                    default_pipeline=data.get("default_pipeline", "default"),
                    default_roles=data.get("default_roles", {}),
                    expected_duration_minutes=data.get("expected_duration_minutes", 60),
                    estimated_cost=data.get("estimated_cost", 0.0),
                    parameters=data.get("parameters", []),
                )
                self.templates[tmpl.name] = tmpl

    def get(self, name):
        return self.templates.get(name)

    def list_templates(self):
        return list(self.templates.keys())
