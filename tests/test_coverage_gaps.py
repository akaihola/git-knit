"""Tests to fill coverage gaps."""

from pytest_check import check
from git_knit.operations.executor_functions import (
    get_config_value,
    set_config_value,
    unset_config_value,
    list_config_keys,
)
from git_knit.operations.config_functions import (
    _get_section,
)


def test_get_config_value_success(fake_process):
    """Test getting a git config value successfully"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "user.name"],
        stdout="John Doe\n"
    )
    result = get_config_value("user", "name")
    assert result == "John Doe"


def test_get_config_value_not_found(fake_process):
    """Test getting a non-existent config value"""
    fake_process.register_subprocess(
        ["git", "config", "--get", "user.nonexistent"],
        returncode=1,
        stdout=""
    )
    result = get_config_value("user", "nonexistent")
    assert result is None


def test_set_config_value(fake_process):
    """Test setting a git config value"""
    fake_process.register_subprocess(
        ["git", "config", "test.key", "value"],
        stdout=""
    )
    set_config_value("test", "key", "value")


def test_unset_config_value(fake_process):
    """Test unsetting a git config value"""
    fake_process.register_subprocess(
        ["git", "config", "--unset", "test.key"],
        stdout=""
    )
    unset_config_value("test", "key")


def test_list_config_keys_empty(fake_process):
    """Test listing config keys when none exist"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^test\\."],
        returncode=1,
        stdout=""
    )
    result = list_config_keys("test")
    assert result == []


def test_list_config_keys_with_values(fake_process):
    """Test listing config keys with values"""
    fake_process.register_subprocess(
        ["git", "config", "--get-regexp", "^test\\."],
        stdout="test.key1 value1\ntest.key2 value2\n"
    )
    result = list_config_keys("test")
    check("key1" in result)
    check("key2" in result)


def test_get_section():
    """Test the _get_section helper function"""
    result = _get_section("my-branch")
    assert result == "knit.my-branch"
