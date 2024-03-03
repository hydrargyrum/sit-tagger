
from sittagger import captiontools

import pytest


@pytest.mark.parametrize(
	"input, expected",
	[
		("#foo", "foo"),
		("#[foo]", "foo"),
		(r"#[fo\]o]", "fo]o"),
		(r"#[fo\\]o]", r"fo\]o"),
	],
)
def test_unhash(input, expected):
	assert captiontools.unhash_tag(input) == expected


@pytest.mark.parametrize(
	"input, expected",
	[
		("foo", "#foo"),
		("fo]o", r"#[fo\]o]"),
		(r"fo\]o", r"#[fo\\\]o]"),
		(r"foo/bar", r"#[foo/bar]"),
	],
)
def test_hash(input, expected):
	assert captiontools.hash_tag(input) == expected


@pytest.mark.parametrize(
	"input, expected",
	[
		("some #foo text in the middle #[of] other", ["foo", "of"]),
		("#start but#foo this is not a #tag", ["start", "tag"]),
	],
)
def test_extract_tags_from_caption(input, expected):
	assert captiontools.extract_tags_from_caption(input) == expected


@pytest.mark.parametrize(
	"input_tags, input_caption, expected",
	[
		(
			["foo", "of"], "some #foo text in the middle #[of] other",
			"some #foo text in the middle #[of] other",
		),
		(
			["foo", "bar"], "the #[foo] tag existed and so did #[baz] but not bar",
			"the #[foo] tag existed and so did but not bar #bar",
		),
		(
			["foo/bar"], "",
			"#[foo/bar]",
		)
	],
)
def test_tags_to_caption(input_tags, input_caption, expected):
	assert captiontools.tags_to_caption(input_tags, input_caption) == expected


@pytest.mark.parametrize(
	"input, expected",
	[
		(" foo\nbar \n", "foo\nbar\n"),
		(" foo  \n  bar", "foo\nbar"),
		("  \n", "\n"),
		(" foo bar  baz   qux    quux", "foo bar baz qux quux"),
	],
)
def test_clean_spaces(input, expected):
	assert captiontools.clean_spaces(input) == expected


@pytest.mark.parametrize(
	"input_caption, old_tag, new_tag, expected",
	[
		(
			"some #foo text in the middle #[of] other", "foo", "bar",
			"some #bar text in the middle #[of] other",
		),
		(
			"the #[foo] tag existed and so did #[baz] but not bar", "foo", "bar",
			"the #bar tag existed and so did #[baz] but not bar",
		),
		(
			"the #[foo] tag existed and so did #[baz] but not bar", "abc", "def",
			"the #[foo] tag existed and so did #[baz] but not bar",
		),
		(
			"the #foo tag is there", "foo", "foo/bar",
			"the #[foo/bar] tag is there",
		)
	],
)
def test_rename_tag_in_caption(input_caption, old_tag, new_tag, expected):
	assert captiontools.rename_tag_in_caption(input_caption, old_tag, new_tag) == expected
