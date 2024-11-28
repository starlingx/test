from keywords.docker.images.object.docker_images_table_parser import DockerImagesTableParser


def test_docker_images_table_parser():
    """
    Tests the docker images table parser
    Returns:

    """

    docker_images_output = [
        'REPOSITORY                                                                  TAG              IMAGE ID       CREATED         SIZE\n',
        'alpine                                                                      latest           1d34ffeaf190   4 weeks ago     7.79MB\n',
        'busybox                                                                     latest           65ad0d468eb1   13 months ago   4.26MB\n',
        'registry.local:9001/busybox                                                 latest           65ad0d468eb1   13 months ago   4.26MB\n',
        'registry.local:9001/docker.io/starlingx/n3000-opae                          stx.8.0-v1.0.2   614615323ea0   21 months ago   321MB\n',
        'registry.local:9001/pv-test                                                 latest           62a12dd7f888   4 years ago     6.94MB\n',
        'gcr.io/google-samples/node-hello                                            1.0              4c7ea8709739   8 years ago     644MB\n',
        'registry.local:9001/node-hello                                              latest           4c7ea8709739   8 years ago     644MB\n',
        '\x1b[?2004hsysadmin@controller-0:~$ \n',
    ]

    table_parser = DockerImagesTableParser(docker_images_output)
    output_values = table_parser.get_output_values_list()

    # tests that the last line is stripped our correctly
    assert len(output_values) == 7, "There are an incorrect number of values"

    first_value = output_values[0]

    assert first_value['REPOSITORY'] == 'alpine'
    assert first_value['TAG'] == 'latest'
    assert first_value['IMAGE ID'] == '1d34ffeaf190'
    assert first_value['CREATED'] == '4 weeks ago'
    assert first_value['SIZE'] == '7.79MB'
