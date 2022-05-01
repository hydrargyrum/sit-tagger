#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

from argparse import ArgumentParser
import os
import sys

from .dbtag import Db


def xdg_config():
	return os.getenv('XDG_CONFIG_HOME', os.getenv('HOME', '/') + '/.config')


def build_parser():
	default_db = os.getenv('SITTAGGER_DATABASE') or xdg_config() + '/sit-tagger.sqlite'

	parser = ArgumentParser(description="Manipulate a SIT-tagger database")
	parser.add_argument('-d', '--database', metavar='FILE', dest='db', default=default_db)
	return parser


def main():
	def do_query():
		if not args.items:
			parser.error('at least one tag should be given')

		for file in db.find_files_by_tags(args.items):
			print(file)

	def do_show():
		if not args.items:
			parser.error('at least one file should be given')

		for file in args.items:
			file = os.path.abspath(file)
			print(file, '=', '[%s]' % ', '.join(db.find_tags_by_file(file)))

	def do_set():
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
			parser.error('at least one file should be provided')
		elif not to_add and not to_del:
			parser.error('at least one tag should be added or removed')

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

	sub = subs.add_parser('set', add_help=False, prefix_chars='^')
	sub.add_argument('items', nargs='+')
	sub.set_defaults(func=do_set)

	sub = subs.add_parser('query', add_help=False, prefix_chars='^')
	sub.add_argument('items', nargs='+')
	sub.set_defaults(func=do_query)

	sub = subs.add_parser('show', description='Show tags associated to files')
	sub.add_argument('items', nargs='+')
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

	sub = subs.add_parser('untrack-files', description='Unlink all tags from a file')
	sub.add_argument('items', nargs='+')
	sub.set_defaults(func=do_untrack_files)

	args = parser.parse_args()

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

