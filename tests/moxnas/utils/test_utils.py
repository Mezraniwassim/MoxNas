"""Tests for MoxNAS utility functions."""

import os
import tempfile
from pathlib import Path
import pytest
import logging
from moxnas.utils import (
    setup_logging,
    check_root_privileges,
    secure_path_join,
    generate_secure_token,
    hash_password,
    verify_hash,
    check_port_available
)

@pytest.fixture
def temp_log_file():
    """Fixture providing a temporary log file path."""
    with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as tmp:
        yield Path(tmp.name)
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

@pytest.fixture
def reset_logging():
    """Fixture to reset logging configuration after each test."""
    yield
    logging.getLogger().handlers.clear()
    logging.getLogger().setLevel(logging.NOTSET)

def test_secure_path_join():
    """Test secure path joining functionality."""
    base = "/tmp/test"
    # Test normal path joining
    result = secure_path_join(base, "subdir", "file.txt")
    assert str(result) == "/tmp/test/subdir/file.txt"
    
    # Test path traversal attempt
    with pytest.raises(ValueError):
        secure_path_join(base, "../etc/passwd")

def test_generate_secure_token():
    """Test secure token generation."""
    token = generate_secure_token()
    assert len(token) == 64  # 32 bytes = 64 hex chars
    assert isinstance(token, str)
    assert all(c in "0123456789abcdef" for c in token)

def test_password_hashing():
    """Test password hashing and verification."""
    password = "test_password"
    salt, hash_value = hash_password(password)
    
    assert verify_hash(password, salt, hash_value)
    assert not verify_hash("wrong_password", salt, hash_value)

def test_check_port_available():
    """Test port availability checking."""
    # Test with likely unused high port
    assert check_port_available(54321)
    
    # Test with typically used system port
    assert not check_port_available(22)  # SSH port, likely in use

@pytest.mark.skipif(os.geteuid() != 0, reason="requires root")
def test_root_privileges():
    """Test root privilege checking."""
    assert check_root_privileges()

def test_setup_logging(temp_log_file, reset_logging):
    """Test logging setup functionality."""
    setup_logging(temp_log_file, debug=True)
    logger = logging.getLogger("test_logger")
    
    test_message = "Test log message"
    logger.debug(test_message)
    
    # Check file contents
    with open(temp_log_file) as f:
        log_content = f.read()
        assert test_message in log_content
    
    # Verify debug level
    assert logger.getEffectiveLevel() == logging.DEBUG
    
    # Test without debug
    setup_logging(temp_log_file, debug=False)
    assert logger.getEffectiveLevel() == logging.INFO