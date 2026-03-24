import pytest


@pytest.fixture(scope="session")
def fixed_tmp_path(tmp_path_factory):
    return tmp_path_factory.mktemp("shared")
