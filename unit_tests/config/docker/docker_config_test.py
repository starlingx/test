"""Unit tests for DockerConfig - Simplified Design."""

import pytest

from config.docker.objects.docker_config import DockerConfig


class TestDockerConfigBasics:
    """Test basic DockerConfig loading and validation."""

    def test_valid_minimal_config(self, tmp_path):
        """Verifies DockerConfig loads with minimal required fields."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "sanity": "resources/image_manifests/stx-sanity-images.yaml"
            }
        }
        """
        )

        config = DockerConfig(str(config_file))

        # Test local_registry
        local_reg = config.get_local_registry()
        assert local_reg.get_registry_url() == "registry.local:9001"
        assert local_reg.get_user_name() == "admin"
        assert local_reg.get_password() == "secret"

        # Test named_manifests
        assert config.get_named_manifest("sanity") == "resources/image_manifests/stx-sanity-images.yaml"

    def test_missing_config_file_raises(self):
        """Verifies FileNotFoundError is raised for a nonexistent config file."""
        with pytest.raises(FileNotFoundError):
            DockerConfig("nonexistent.json5")

    def test_missing_local_registry_raises(self, tmp_path):
        """Verifies ValueError is raised when local_registry is missing."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "named_manifests": {
                "sanity": "stx-sanity-images.yaml"
            }
        }
        """
        )

        with pytest.raises(ValueError, match="Config missing required field: 'local_registry'"):
            DockerConfig(str(config_file))

    def test_missing_named_manifests_raises(self, tmp_path):
        """Verifies ValueError is raised when named_manifests is missing."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            }
        }
        """
        )

        with pytest.raises(ValueError, match="Config missing required field: 'named_manifests'"):
            DockerConfig(str(config_file))


class TestNamedManifests:
    """Test named manifest functionality."""

    def test_get_named_manifest_success(self, tmp_path):
        """Verifies get_named_manifest() returns correct path."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "sanity": "resources/image_manifests/stx-sanity-images.yaml",
                "networking": "resources/image_manifests/stx-networking-images.yaml",
                "starlingx": "resources/image_manifests/starlingx-dockerhub-images.yaml"
            }
        }
        """
        )

        config = DockerConfig(str(config_file))

        assert config.get_named_manifest("sanity") == "resources/image_manifests/stx-sanity-images.yaml"
        assert config.get_named_manifest("networking") == "resources/image_manifests/stx-networking-images.yaml"
        assert config.get_named_manifest("starlingx") == "resources/image_manifests/starlingx-dockerhub-images.yaml"

    def test_get_named_manifest_not_found_raises(self, tmp_path):
        """Verifies get_named_manifest() raises ValueError for unknown name."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "sanity": "stx-sanity-images.yaml"
            }
        }
        """
        )

        config = DockerConfig(str(config_file))

        with pytest.raises(ValueError, match="Named manifest 'unknown' not found"):
            config.get_named_manifest("unknown")

    def test_get_all_named_manifests(self, tmp_path):
        """Verifies get_named_manifests() returns all manifests."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "sanity": "stx-sanity-images.yaml",
                "networking": "stx-networking-images.yaml"
            }
        }
        """
        )

        config = DockerConfig(str(config_file))
        manifests = config.get_named_manifests()

        assert len(manifests) == 2
        assert manifests["sanity"] == "stx-sanity-images.yaml"
        assert manifests["networking"] == "stx-networking-images.yaml"


class TestSourceRegistryAuthentication:
    """Test source registry authentication functionality."""

    def test_get_source_registry_for_dockerhub_image(self, tmp_path):
        """Verifies get_source_registry_for_image() returns DockerHub credentials."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "starlingx": "starlingx-dockerhub-images.yaml"
            },
            "source_registries": {
                "docker.io": {
                    "username": "testuser",
                    "password": "testpass"
                }
            }
        }
        """
        )
        config = DockerConfig(str(config_file))

        # Test with explicit docker.io hostname
        registry = config.get_source_registry_for_image("docker.io/library/busybox:1.36.1")
        assert registry is not None
        assert registry.get_registry_url() == "docker.io"
        assert registry.get_user_name() == "testuser"
        assert registry.get_password() == "testpass"

        # Test with DockerHub namespace
        registry = config.get_source_registry_for_image("docker.io/starlingx/stx-platformclients:master")
        assert registry is not None
        assert registry.get_registry_url() == "docker.io"

    def test_get_source_registry_for_harbor_image(self, tmp_path):
        """Verifies get_source_registry_for_image() returns Harbor credentials."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "custom": "custom-harbor-images.yaml"
            },
            "source_registries": {
                "harbor.example.com:443": {
                    "username": "harboruser",
                    "password": "harborpass"
                }
            }
        }
        """
        )
        config = DockerConfig(str(config_file))

        # Test with Harbor registry URL with port
        registry = config.get_source_registry_for_image("harbor.example.com:443/myproject/myapp:v1.0.0")
        assert registry is not None
        assert registry.get_registry_url() == "harbor.example.com:443"
        assert registry.get_user_name() == "harboruser"
        assert registry.get_password() == "harborpass"

    def test_get_source_registry_for_unconfigured_registry(self, tmp_path):
        """Verifies get_source_registry_for_image() returns None for unconfigured registries."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "sanity": "stx-sanity-images.yaml"
            },
            "source_registries": {
                "docker.io": {
                    "username": "testuser",
                    "password": "testpass"
                }
            }
        }
        """
        )
        config = DockerConfig(str(config_file))

        # Test with registry that has no source_registries entry
        registry = config.get_source_registry_for_image("gcr.io/project/image:tag")
        assert registry is None

        # Test with different registry
        registry = config.get_source_registry_for_image("registry.k8s.io/pause:3.9")
        assert registry is None

    def test_get_source_registry_with_multiple_registries(self, tmp_path):
        """Verifies get_source_registry_for_image() matches correct registry from multiple configs."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "combined": "combined-images.yaml"
            },
            "source_registries": {
                "docker.io": {
                    "username": "dockeruser",
                    "password": "dockerpass"
                },
                "harbor.corporate.com:8443": {
                    "username": "harboruser",
                    "password": "harborpass"
                },
                "registry.local:5000": {
                    "username": "localuser",
                    "password": "localpass"
                }
            }
        }
        """
        )
        config = DockerConfig(str(config_file))

        # Test DockerHub match
        registry = config.get_source_registry_for_image("docker.io/busybox:1.36.1")
        assert registry.get_user_name() == "dockeruser"

        # Test Harbor match
        registry = config.get_source_registry_for_image("harbor.corporate.com:8443/project/image:v1.0")
        assert registry.get_user_name() == "harboruser"

        # Test local registry match
        registry = config.get_source_registry_for_image("registry.local:5000/myimage:latest")
        assert registry.get_user_name() == "localuser"

    def test_get_source_registry_with_no_source_registries_config(self, tmp_path):
        """Verifies get_source_registry_for_image() returns None when source_registries not configured."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "sanity": "stx-sanity-images.yaml"
            }
        }
        """
        )
        config = DockerConfig(str(config_file))

        # Test returns None when source_registries section doesn't exist
        registry = config.get_source_registry_for_image("docker.io/busybox:1.36.1")
        assert registry is None

    def test_get_source_registry_hostname_matching(self, tmp_path):
        """Verifies get_source_registry_for_image() correctly extracts and matches hostname."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "harbor": "harbor-images.yaml"
            },
            "source_registries": {
                "harbor.example.com": {
                    "username": "user",
                    "password": "pass"
                }
            }
        }
        """
        )
        config = DockerConfig(str(config_file))

        # Test matches hostname before first path separator
        registry = config.get_source_registry_for_image("harbor.example.com/project/nested/path/image:tag")
        assert registry is not None
        assert registry.get_registry_url() == "harbor.example.com"

    def test_source_registry_with_special_characters_in_password(self, tmp_path):
        """Verifies source_registries handles special characters in passwords."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "starlingx": "starlingx-dockerhub-images.yaml"
            },
            "source_registries": {
                "docker.io": {
                    "username": "user",
                    "password": "sodh#$b)aIO2"
                }
            }
        }
        """
        )
        config = DockerConfig(str(config_file))

        # Password with special shell characters should be stored correctly
        registry = config.get_source_registry_for_image("docker.io/image:tag")
        assert registry is not None
        assert registry.get_password() == "sodh#$b)aIO2"  # Exact match, no escaping at this level

    def test_get_source_registry_matches_exact_registry_boundaries(self, tmp_path):
        """Verifies get_source_registry_for_image() matches registry at proper boundaries (before first '/')."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "sanity": "stx-sanity-images.yaml"
            },
            "source_registries": {
                "registry.io": {
                    "username": "gooduser",
                    "password": "goodpass"
                }
            }
        }
        """
        )
        config = DockerConfig(str(config_file))

        # Should match when registry URL is exactly at the boundary (before first '/')
        registry = config.get_source_registry_for_image("registry.io/myapp/image:v1.0")
        assert registry is not None
        assert registry.get_registry_url() == "registry.io"

        # Should NOT match when registry appears to be a substring of a different hostname
        # Docker image format: <registry>/<path>, so registry must be followed by '/'
        registry = config.get_source_registry_for_image("registry.io.example.com/other/image:latest")
        assert registry is None, "Different registry hostname that happens to start with same prefix"

        # Should NOT match when port differs from configured registry
        # Config has "registry.io" (no port), image has "registry.io:5000" (with port)
        registry = config.get_source_registry_for_image("registry.io:5000/app/image:v2.0")
        assert registry is None, "Different port means different registry"

    def test_get_source_registry_avoids_port_number_prefix_collisions(self, tmp_path):
        """Verifies registry matching doesn't confuse similar port numbers like :500 vs :5000."""
        config_file = tmp_path / "docker_config.json5"
        config_file.write_text(
            """
        {
            "local_registry": {
                "url": "registry.local:9001",
                "username": "admin",
                "password": "secret"
            },
            "named_manifests": {
                "sanity": "stx-sanity-images.yaml"
            },
            "source_registries": {
                "harbor.example.com:500": {
                    "username": "user500",
                    "password": "pass500"
                },
                "harbor.example.com:5000": {
                    "username": "user5000",
                    "password": "pass5000"
                }
            }
        }
        """
        )
        config = DockerConfig(str(config_file))

        # Should match exact registry with port :500
        registry = config.get_source_registry_for_image("harbor.example.com:500/project/image:v1")
        assert registry is not None
        assert registry.get_registry_url() == "harbor.example.com:500"
        assert registry.get_user_name() == "user500"

        # Should match exact registry with port :5000
        registry = config.get_source_registry_for_image("harbor.example.com:5000/project/image:v1")
        assert registry is not None
        assert registry.get_registry_url() == "harbor.example.com:5000"
        assert registry.get_user_name() == "user5000"

        # Should NOT match :500 when image has :5000 (even though "500" is prefix of "5000")
        # The '/' boundary prevents this prefix confusion
        registry = config.get_source_registry_for_image("harbor.example.com:5001/project/image:v1")
        assert registry is None, "Port :5001 doesn't match either :500 or :5000"
