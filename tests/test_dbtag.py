# SPDX-License-Identifier: WTFPL

import os

import pytest

from sittagger import dbtag


@pytest.fixture
def db(db_path):
	result = dbtag.Db()
	result.open(db_path)
	result.do_migrations()
	yield result
	os.unlink(db_path)


@pytest.fixture
def a_few_tags(db):
	db.tag_file("/foo", ["tag1", "tag3"])
	db.tag_file("/bar", ["tag2", "tag3"])


def test_tag_file_untag(db):
	db.tag_file("/foo", ["tag1"])
	assert set(db.find_tags_by_file("/foo")) == {"tag1"}
	assert set(db.find_tags_by_file("/bar")) == set()

	db.tag_file("/foo", ["tag2", "tag3"])
	assert set(db.find_tags_by_file("/foo")) == {"tag1", "tag2", "tag3"}

	db.untag_file("/foo", ["tag2"])
	assert set(db.find_tags_by_file("/foo")) == {"tag1", "tag3"}

	db.tag_file("/bar", ["tag2", "tag3"])
	assert set(db.find_tags_by_file("/foo")) == {"tag1", "tag3"}
	assert set(db.find_tags_by_file("/bar")) == {"tag2", "tag3"}


def test_list_tags_and_files(db, a_few_tags):
	assert set(db.list_tags()) == {"tag1", "tag2", "tag3"}
	assert set(db.list_files()) == {"/foo", "/bar"}

	db.untag_file("/foo", ["tag1", "tag3"])
	assert set(db.list_tags()) == {"tag2", "tag3"}
	assert set(db.list_files()) == {"/bar"}


def test_find_files_by_tags(db, a_few_tags):
	assert set(db.find_files_by_tags(["tag1"])) == {"/foo"}
	assert set(db.find_files_by_tags(["tag2"])) == {"/bar"}
	assert set(db.find_files_by_tags(["tag3"])) == {"/foo", "/bar"}
	assert set(db.find_files_by_tags(["tag3", "tag1"])) == {"/foo"}


def test_remove_file(db, a_few_tags):
	db.remove_file("/foo")
	assert set(db.find_files_by_tags(["tag1"])) == set()
	assert set(db.find_tags_by_file("/foo")) == set()
	assert set(db.list_files()) == {"/bar"}
	assert set(db.list_tags()) == {"tag2", "tag3"}


def test_remove_tag(db, a_few_tags):
	db.remove_tag("tag3")
	assert set(db.find_files_by_tags(["tag3"])) == set()
	assert set(db.find_tags_by_file("/foo")) == {"tag1"}
	assert set(db.list_tags()) == {"tag2", "tag1"}


def test_rename_tag(db, a_few_tags):
	db.rename_tag("tag3", "tag4")
	assert set(db.find_files_by_tags(["tag3"])) == set()
	assert set(db.find_files_by_tags(["tag4"])) == {"/foo", "/bar"}
	assert set(db.find_tags_by_file("/foo")) == {"tag1", "tag4"}
	assert set(db.list_tags()) == {"tag2", "tag1", "tag4"}


def test_rename_file(db, a_few_tags):
	db.rename_file("/foo", "/folder/new")
	assert set(db.find_files_by_tags(["tag3"])) == {"/folder/new", "/bar"}
	assert set(db.find_tags_by_file("/folder/new")) == {"tag1", "tag3"}
	assert set(db.find_tags_by_file("/foo")) == set()
	assert set(db.list_files()) == {"/folder/new", "/bar"}


def test_rename_folder(db, a_few_tags):
	db.rename_file("/foo", "/barfolder/new")
	db.rename_folder("/barfolder", "/other")
	assert set(db.find_files_by_tags(["tag3"])) == {"/other/new", "/bar"}
	assert set(db.find_tags_by_file("/other/new")) == {"tag1", "tag3"}
	assert set(db.find_tags_by_file("/foo")) == set()
	assert set(db.list_files()) == {"/other/new", "/bar"}
