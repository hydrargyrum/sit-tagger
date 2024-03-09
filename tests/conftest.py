# SPDX-License-Identifier: WTFPL

import os
import subprocess
import tempfile

import pytest


@pytest.fixture
def image_factory(tmp_path):
	def factory():
		_, filename = tempfile.mkstemp(dir=tmp_path, suffix=".png")
		files.append(filename)
		subprocess.check_call(["convert", "-size", "10x10", "xc:red", filename])
		return filename

	files = []
	yield factory
	for file in files:
		os.unlink(file)


@pytest.fixture
def db_path(tmp_path):
	return tmp_path / "tags.sqlite"
