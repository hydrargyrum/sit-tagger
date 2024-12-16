# SIT-Tagger

SIT-Tagger is an app for browsing tagged files.

For now, it consists in an image browser app, that allows to set custom
text tags on any image file, and then list image files matching checked
tags. The tags are saved in a local SQLite database.

Other apps reusing the same database will be added, and support for
video files will be added.

![sit-tagger window with a directory tree pane and the list of files (with thumbnails) from the selected dir](https://raw.githubusercontent.com/hydrargyrum/sit-tagger/master/docs/shot-dirview.jpg)

![sit-tagger window with a tags list pane (with a checkbox for each tag) and the list of files (with thumbnails) matching the checked tags](https://raw.githubusercontent.com/hydrargyrum/sit-tagger/master/docs/shot-tagview.jpg)

It also comes with a command-line tool to manipulate the tag database.

## Captions

SIT-Tagger lets you write text captions for files. In addition, any `#hashtags` you write in the caption are transformed into actual file tags. This makes tagging files easier while letting you comment your files.

![sit-tagger window with the list of files (with thumbnails) and a caption editor pane (showing a user-entered caption with #hashtags in it)](https://raw.githubusercontent.com/hydrargyrum/sit-tagger/master/docs/shot-caption.jpg)

## Command-line tool

SIT-Tagger comes with a command-line tool to manipulate the tag
database.

These 2 commands set tag foo and unset tag bar on some/file.jpg:

    sit-tagger-cli set +foo some/file.jpg
    sit-tagger-cli set -bar some/file.jpg

Combined in a single command:

    sit-tagger-cli set +foo -bar some/file.jpg

It\'s possible to query the list files tagged foo:

    % sit-tagger-cli query foo
    /tmp/some/file.jpg

Or show the tags of a file:

    % sit-tagger-cli show some/file.jpg
    /tmp/some/file.jpg = [foo]

List all tags:

    % sit-tagger-cli list-tags
    foo

Rename a tag:

    sit-tagger-cli rename-tag foo foonew

List all files:

    % sit-tagger-cli list-files
    /tmp/some/file.jpg

Remove all tags from a file:

    sit-tagger-cli untrack-files some/file.jpg

## Install

Install with [`pipx install sittagger`](https://pypi.org/project/sittagger/).
