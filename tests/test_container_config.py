from pathlib import Path

import yaml


def test_compose_has_only_required_services():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    assert set(compose["services"]) == {"db", "web"}


def test_standard_dockerfile_exists():
    assert Path("Dockerfile").is_file()
    assert not Path("Dockefile").exists()
