#!/usr/bin/env python3

from argparse import ArgumentParser
import os

from .dbtag import Db


def xdg_config():
	return os.getenv('XDG_CONFIG_HOME', os.getenv('HOME', '/') + '/.config')


def build_parser():
	parser = ArgumentParser()
	parser.add_argument('-d', '--database', metavar='FILE', dest='db', default=xdg_config() + '/sit-tagger.sqlite')
	return parser


def main():
	def do_query(args, items):
		if not items:
			parser.error('at least one tag should be given')

		for file in db.find_files_by_tags(items):
			print(file)

	def do_show(args, items):
		if not items:
			parser.error('at least one file should be given')

		for file in items:
			file = os.path.abspath(file)
			print(file, '=', '[%s]' % ', '.join(db.find_tags_by_file(file)))

	def do_set(args, items):
		to_add = set()
		to_del = set()
		files = []
		for item in items:
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

		for file in files:
			file = os.path.abspath(file)

			for tag in to_add:
				db.tag_file(file, tag)
			for tag in to_del:
				db.untag_file(file, tag)

	cmds = {
		'set': do_set,
		'show': do_show,
		'query': do_query,
	}

	parser = build_parser()
	parser.add_argument('subcommand', choices=cmds.keys())
	args, items = parser.parse_known_args()

	db = Db()
	db.open(args.db)
	try:
		with db:
			db.create_tables()
			cmds[args.subcommand](args, items)
	finally:
		db.close()


if __name__ == '__main__':
	main()

