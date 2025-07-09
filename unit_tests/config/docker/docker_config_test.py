import pytest

from config.docker.objects.docker_config import DockerConfig


def test_valid_json5_parses_and_getters(tmp_path):
    """Verifies DockerConfig loads JSON5 and retrieves default registry and manifests."""
    config_file = tmp_path / "docker_config.json5"
    config_file.write_text(
        """
    {
        "default_source_registry": "dockerhub",
        "image_manifest_files": ["dummy.yaml"],
        "registries": {
            "dockerhub": {
                "registry_name": "dockerhub",
                "registry_url": "docker.io",
                "user_name": "",
                "password": ""
            }
        }
    }
    """
    )

    config = DockerConfig(str(config_file))

    assert config.get_default_source_registry_name() == "dockerhub"
    assert config.get_image_manifest_files() == ["dummy.yaml"]

    reg = config.get_registry("dockerhub")
    assert reg.get_registry_name() == "dockerhub"
    assert reg.get_registry_url() == "docker.io"


def test_missing_config_file_raises():
    """Verifies FileNotFoundError is raised for a nonexistent config file."""
    with pytest.raises(FileNotFoundError):
        DockerConfig("nonexistent.json5")


def test_get_registry_invalid_raises(tmp_path):
    """Verifies ValueError is raised when an unknown registry name is requested."""
    config_file = tmp_path / "docker_config.json5"
    config_file.write_text(
        """
    {
        "default_source_registry": "dockerhub",
        "image_manifest_files": [],
        "registries": {
            "dockerhub": {
                "registry_name": "dockerhub",
                "registry_url": "docker.io",
                "user_name": "",
                "password": ""
            }
        }
    }
    """
    )

    config = DockerConfig(str(config_file))

    with pytest.raises(ValueError, match="No registry with the name 'invalid' was found"):
        config.get_registry("invalid")


def test_resolve_override_true_manifest_registry(tmp_path):
    """Verifies override=true returns the manifest manifest_registry."""
    config_file = tmp_path / "docker_config.json5"
    config_file.write_text(
        """
    {
        "default_source_registry": "dockerhub",
        "image_manifest_files": [],
        "manifest_registry_map": {
            "file.yaml": {
                "manifest_registry": "harbor",
                "override": true
            }
        },
        "registries": {
            "dockerhub": {
                "registry_name": "dockerhub",
                "registry_url": "docker.io",
                "user_name": "",
                "password": ""
            },
            "harbor": {
                "registry_name": "harbor",
                "registry_url": "harbor.local",
                "user_name": "",
                "password": ""
            }
        }
    }
    """
    )
    config = DockerConfig(str(config_file))
    result = config.get_effective_source_registry_name({}, "file.yaml")
    assert result == "harbor"


def test_resolve_override_false_per_image(tmp_path):
    """Verifies override=false uses per-image source_registry when present."""
    config_file = tmp_path / "docker_config.json5"
    config_file.write_text(
        """
    {
        "default_source_registry": "dockerhub",
        "image_manifest_files": [],
        "manifest_registry_map": {
            "file.yaml": {
                "manifest_registry": "harbor",
                "override": false
            }
        },
        "registries": {
            "dockerhub": {
                "registry_name": "dockerhub",
                "registry_url": "docker.io",
                "user_name": "",
                "password": ""
            },
            "harbor": {
                "registry_name": "harbor",
                "registry_url": "harbor.local",
                "user_name": "",
                "password": ""
            },
            "gcr": {
                "registry_name": "gcr",
                "registry_url": "gcr.io",
                "user_name": "",
                "password": ""
            }
        }
    }
    """
    )
    config = DockerConfig(str(config_file))
    result = config.get_effective_source_registry_name({"source_registry": "gcr"}, "file.yaml")
    assert result == "gcr"


def test_resolve_override_false_manifest_registry(tmp_path):
    """Verifies override=false uses manifest manifest_registry if no per-image source_registry."""
    config_file = tmp_path / "docker_config.json5"
    config_file.write_text(
        """
    {
        "default_source_registry": "dockerhub",
        "image_manifest_files": [],
        "manifest_registry_map": {
            "file.yaml": {
                "manifest_registry": "harbor",
                "override": false
            }
        },
        "registries": {
            "dockerhub": {
                "registry_name": "dockerhub",
                "registry_url": "docker.io",
                "user_name": "",
                "password": ""
            },
            "harbor": {
                "registry_name": "harbor",
                "registry_url": "harbor.local",
                "user_name": "",
                "password": ""
            }
        }
    }
    """
    )
    config = DockerConfig(str(config_file))
    result = config.get_effective_source_registry_name({}, "file.yaml")
    assert result == "harbor"


def test_resolve_no_manifest_entry_per_image(tmp_path):
    """Verifies resolution uses per-image source_registry when no manifest entry exists."""
    config_file = tmp_path / "docker_config.json5"
    config_file.write_text(
        """
    {
        "default_source_registry": "dockerhub",
        "image_manifest_files": [],
        "registries": {
            "dockerhub": {
                "registry_name": "dockerhub",
                "registry_url": "docker.io",
                "user_name": "",
                "password": ""
            },
            "gcr": {
                "registry_name": "gcr",
                "registry_url": "gcr.io",
                "user_name": "",
                "password": ""
            }
        }
    }
    """
    )
    config = DockerConfig(str(config_file))
    result = config.get_effective_source_registry_name({"source_registry": "gcr"}, "unknown.yaml")
    assert result == "gcr"


def test_resolve_no_manifest_entry_default(tmp_path):
    """Verifies resolution falls back to default registry if no manifest entry or per-image source_registry."""
    config_file = tmp_path / "docker_config.json5"
    config_file.write_text(
        """
    {
        "default_source_registry": "dockerhub",
        "image_manifest_files": [],
        "registries": {
            "dockerhub": {
                "registry_name": "dockerhub",
                "registry_url": "docker.io",
                "user_name": "",
                "password": ""
            }
        }
    }
    """
    )
    config = DockerConfig(str(config_file))
    result = config.get_effective_source_registry_name({}, "unknown.yaml")
    assert result == "dockerhub"


def test_override_true_with_null_registry_fails_in_init(tmp_path):
    """Verifies ValueError is raised during init if override=true and manifest_registry is null."""
    config_file = tmp_path / "docker_config.json5"
    config_file.write_text(
        """
    {
        "default_source_registry": "dockerhub",
        "image_manifest_files": [],
        "manifest_registry_map": {
            "some.yaml": {
                "manifest_registry": null,
                "override": true
            }
        },
        "registries": {
            "dockerhub": {
                "registry_name": "dockerhub",
                "registry_url": "docker.io",
                "user_name": "",
                "password": ""
            }
        }
    }
    """
    )
    with pytest.raises(ValueError, match="override=true requires 'manifest_registry' to be set"):
        DockerConfig(str(config_file))
