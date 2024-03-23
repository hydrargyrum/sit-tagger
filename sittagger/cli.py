#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

from argparse import ArgumentParser, RawTextHelpFormatter
from pathlib import Path
from textwrap import dedent
import os
import sys

from .dbtag import Db


def xdg_config():
	return os.getenv('XDG_CONFIG_HOME', os.getenv('HOME', '/') + '/.config')


def xdg_data():
	return os.getenv('XDG_DATA_HOME', str(Path.home() / ".local/share"))


def choose_db_path(opts):
	if opts.db:  # 1. --database
		return

	opts.db = os.getenv("SITTAGGER_DATABASE")  # 2. env var
	if opts.db:
		return

	legacy_path = Path(xdg_config()) / 'sit-tagger.sqlite'
	dest_path = Path(xdg_data()) / 'sit-tagger/files.sqlite'

	for preferred in (dest_path, legacy_path):  # 3. new location or legacy
		if preferred.exists():
			opts.db = str(preferred)
			return

	# 4. none found: use new location
	dest_path.parent.mkdir(mode=0o700, exist_ok=True)
	opts.db = str(dest_path)


def build_parser():
	parser = ArgumentParser(description="Manipulate a SIT-tagger database")
	parser.add_argument('-d', '--database', metavar='FILE', dest='db')
	return parser


def main():
	def do_query():
		if not args.items or args.items in (['-h'], ['--help']):
			sub_query.print_help()
			sub_query.error('at least one tag should be given')

		for file in db.find_files_by_tags(args.items):
			print(file)

	def do_show():
		if not args.items:
			parser.error('at least one file should be given')

		for file in args.items:
			file = os.path.abspath(file)
			print(file, '=', '[%s]' % ', '.join(db.find_tags_by_file(file)))

	def do_set():
		if not args.items or args.items in (['-h'], ['--help']):
			sub_set.print_help()
			sub_set.error("at least one file should be provided")

		to_add = set()
		to_del = set()
		files = []
		for item in args.items:
			if item.startswith('-'):
				to_del.add(item[1:])
			elif item.startswith('+'):
				to_add.add(item[1:])
			else:
				files.append(item)

		if not files:
			sub_set.print_help()
			sub_set.error('at least one file should be provided')
		elif not to_add and not to_del:
			sub_set.print_help()
			sub_set.error('at least one tag should be added or removed')

		err = 0
		for file in files:
			file = os.path.abspath(file)
			if not os.path.exists(file):
				print('will not tag non-existing file %r' % file, file=sys.stderr)
				err = 1
				continue

			for tag in to_add:
				db.tag_file(file, tag)
			for tag in to_del:
				db.untag_file(file, tag)

		return err

	def do_set_caption():
		if args.keep_existing_tags:
			existing_tags = db.find_tags_by_file(args.file)
		db.set_caption(args.file, args.caption)
		if args.keep_existing_tags:
			db.tag_file(args.file, existing_tags)

	def do_get_caption():
		caption = db.get_caption(args.file)
		if caption:
			print(caption)

	def do_rename_tag():
		db.rename_tag(args.src, args.dst)

	def do_rename_file():
		if not os.path.exists(args.dst):
			parser.error('will not rename non-existing dest file %r' % args.dst)

		args.src = os.path.abspath(args.src)
		args.dst = os.path.abspath(args.dst)

		if args.recursive:
			db.rename_folder(args.src, args.dst)
		else:
			db.rename_file(args.src, args.dst)

	def do_list_tags():
		for tag in db.list_tags():
			print(tag)

	def do_list_files():
		for file in db.list_files():
			print(file)

	def do_untrack_files():
		for item in args.items:
			item = os.path.abspath(item)
			db.untrack_file(item)

	parser = build_parser()
	subs = parser.add_subparsers(dest='subcommand', required=True)

	sub_set = sub = subs.add_parser(
		'set', add_help=False, prefix_chars='^',
		description='Set/unset tags',
		epilog=dedent('''
			Example:

				%(prog)s set +foo -bar some_file.jpg

			will add "foo" tag to "some_file.jpg" and delete "bar" tag from "some_file.jpg"
		'''),
		formatter_class=RawTextHelpFormatter,
	)
	sub.add_argument(
		'items', nargs='*', metavar='ITEM',
		help=dedent('''
			an ITEM can be either:
			- a filename to manipulate it
			- or "+TAG" to add TAG
			- or "-TAG" to remove a TAG
		'''),
	)
	sub.set_defaults(func=do_set)

	sub = subs.add_parser(
		"get-caption", description="Get caption of file",
	)
	sub.add_argument("file", help="File whose caption will be shown")
	sub.set_defaults(func=do_get_caption)

	sub = subs.add_parser(
		"set-caption", description="Set caption of file",
	)
	sub.add_argument("--keep-existing-tags", action="store_true")
	sub.add_argument("file", help="File whose caption will be changed")
	sub.add_argument("caption", help="New text caption (can contain #tags)")
	sub.set_defaults(func=do_set_caption)

	sub_query = sub = subs.add_parser(
		'query', add_help=False, prefix_chars='^',
		description='Search files matching TAGs',
		epilog=dedent('''
			Example:

				%(prog)s query foo bar

			will list files having both "foo" AND "bar" tags
		'''),
		formatter_class=RawTextHelpFormatter,
	)
	sub.add_argument(
		'items', nargs='*',
		metavar='TAG',
		help='tags that should be searched',
	)
	sub.set_defaults(func=do_query)

	sub = subs.add_parser('show', description='Show tags associated to files')
	sub.add_argument('items', nargs='+', metavar='file')
	sub.set_defaults(func=do_show)

	sub = subs.add_parser('rename-tag', description='Rename a tag (and keep linked files to it)')
	sub.add_argument('src', help='Current name of the tag')
	sub.add_argument('dst', help='New name of the tag')
	sub.set_defaults(func=do_rename_tag)

	sub = subs.add_parser('rename-file', description='Consider a file renamed, keep linked tags to it (does not move the file on-disk)')
	sub.add_argument('--recursive', action='store_true', help='src and dst are folders, move their content')
	sub.add_argument('src', help='Old name/path of file')
	sub.add_argument('dst', help='New name/path of file')
	sub.set_defaults(func=do_rename_file)

	sub = subs.add_parser('list-tags', description='List all tags')
	sub.set_defaults(func=do_list_tags)

	sub = subs.add_parser('list-files', description='List tagged files')
	sub.set_defaults(func=do_list_files)

	sub = subs.add_parser('untrack-files', description='Unlink all tags from a file (does not remove files on-disk)')
	sub.add_argument('items', nargs='+')
	sub.set_defaults(func=do_untrack_files)

	args = parser.parse_args()
	choose_db_path(args)

	db = Db()
	db.open(args.db)
	try:
		with db:
			db.do_migrations()
			err = args.func()
	finally:
		db.close()

	if err:
		return 1
	return 0


if __name__ == '__main__':
	sys.exit(main())
