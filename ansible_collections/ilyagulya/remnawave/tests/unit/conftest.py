# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ilya Gulya
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""Pytest configuration for Remnawave Ansible collection unit tests."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest


@pytest.fixture
def mock_module(mocker):
    """Create a mock Ansible module object."""
    module = mocker.MagicMock()
    module.check_mode = False
    module.params = {}
    return module
