# SPDX-License-Identifier: WTFPL

import re


CAPTION_TAG = re.compile(r"(?:^|(?<=\s))(?:#[\w-]+|#\[(?:\\.|[^]])+\])")
COMPLEX_TAG_PATTERN = re.compile(r"[^\w-]")
TO_ESCAPE = re.compile(r"([][\\])")
UNWANTED_SPACES = re.compile(r"^ +|(?<= ) | +$", flags=re.M)


def unhash_tag(tag):
	tag = tag.removeprefix("#").removeprefix("[").removesuffix("]")
	return re.sub(r"\\(.)", r"\1", tag)


def hash_tag(tag):
	if not COMPLEX_TAG_PATTERN.search(tag):
		return f"#{tag}"
	escaped = TO_ESCAPE.sub(r"\\\1", tag)
	return f"#[{escaped}]"


def extract_tags_from_caption(caption):
	return [unhash_tag(htag) for htag, _, _ in extract_tags_with_positions(caption)]
	# return [unhash_tag(htag) for htag in CAPTION_TAG.findall(caption)]


def extract_tags_with_positions(caption):
	for match in CAPTION_TAG.finditer(caption):
		yield (unhash_tag(match[0]), match.start(), match.end())


def rename_tag_in_caption(caption, old, new):
	for caption_tag, start, end in extract_tags_with_positions(caption):
		if caption_tag == old:
			caption = f"{caption[:start]} {hash_tag(new)} {caption[end:]}"
			caption = clean_spaces(caption)
			break
	return caption


def clean_spaces(s):
	return UNWANTED_SPACES.sub("", s)


def tags_to_caption(tags, caption):
	tags_positions = list(extract_tags_with_positions(caption))
	old_tags = {htag for htag, _, _ in tags_positions}
	new_tags = set(tags)
	to_delete = old_tags - new_tags
	to_add = new_tags - old_tags

	if to_delete:
		charlist = list(caption)
		for htag, start, end in tags_positions[::-1]:
			if htag in to_delete:
				del charlist[start:end]
		caption = "".join(charlist)
	caption = clean_spaces(caption)

	if to_add:
		if caption:
			caption += " "
		caption += " ".join(hash_tag(tag) for tag in to_add)
	return caption
