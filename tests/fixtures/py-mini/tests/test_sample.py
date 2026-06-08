"""Golden fixture for the Python adapter."""


def test_fully_documented_requirement_renders():
    """
    @spec.given a python test with a spec docstring
    @spec.when  the python adapter parses it
    @spec.then  it yields one Requirement with a complete spec
    @spec.us    US-002-python-story
    """
    assert True


def test_undocumented_python_test_is_flagged():
    assert True
