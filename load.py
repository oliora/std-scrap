# coding=utf-8

from __future__ import print_function

__author__ = "oliora"
__copyright__ = "Copyright (C) 2015 oliora"

import json
import sys
import argparse
import couchdb
import codecs
import urlparse


def load(db, doc, update=False):
    doc = couchdb.Document(doc)
    doc['_id'] = doc['number']
    try:
        db.save(doc)
        return 1
    except couchdb.ResourceConflict:
        if not update:
            raise
        else:
            doc['_rev'] = db[doc.id].rev
            db.save(doc)
            return 0


def split_db_url(db_url):
    """
    Splits db_url into (server_path, db_name)
    """
    url_parts = urlparse.urlparse(db_url)
    path_parts = url_parts[2].split('/')
    db_name = path_parts[-1]
    server_path = '/'.join(path_parts[:-1])
    #if not server_path:
        #server_path = '/'
    server_url = urlparse.urlunsplit((url_parts[0],
                                      url_parts[1],
                                      server_path,
                                      url_parts[3],
                                      url_parts[4]))
    return server_url, db_name



def main():
    parser = argparse.ArgumentParser(description='Load parsed std-documents file and put to CouchDB')
    parser.add_argument('input', nargs='+', help='JSON file(s) to load')
    parser.add_argument('--update', action='store_true', help='If doc already exists, update it')
    parser.add_argument('--create', action='store_true', help='Create DB if not exists')
    parser.add_argument('--clean-first', action='store_true', help='Delete DB')
    parser.add_argument('--db', default='http://127.0.0.1:5984/std-scrap',
                        help='CouchDB database URL (default: http://127.0.0.1:5984/std-scrap)')

    args = parser.parse_args()

    server_url, db_name = split_db_url(args.db)

    db = couchdb.Database(args.db)

    if not db:
        if args.create:
            print('Create DB \'{0}\' at server \'{1}\'.'.format(db_name, server_url))
            db = couchdb.Server(server_url).create(db_name)
        else:
            raise Exception('DB does not exists. Please specify --create to create it.')
    else:
        if args.clean_first:
            print('Recreate DB \'{0}\' at server \'{1}\''.format(db_name, server_url))
            del couchdb.Server(server_url)[db_name]
            db = couchdb.Server(server_url).create(db_name)

    total = 0
    updated = 0
    errors = []

    for filename in args.input:
        with open(filename, 'r') as f:
            docs = json.load(f)
        for doc in docs:
            try:
                # TODO: move into load()
                if doc['number'] == '' or doc['number'].startswith('SD'):
                    continue

                if not load(db, doc, args.update):
                    updated += 1
                total += 1
            except Exception, e:
                errors.append((doc['number'], filename, unicode(e)))

    if not errors:
        print('Loaded {0} documents from {1} files: {2} added, {3} updated, no errors detected.'.format(
            total, len(args.input), total - updated, updated))
    else:
        for e in errors:
            print(codecs.encode(u'Error when loading doc \'{0}\': {2} [{1}]'.format(e[0], e[1], e[2]),
                                'ascii', 'xmlcharrefreplace'), file=sys.stderr)
        print('\nLoaded {0} documents from {1} files: {2} added, {3} updated, {4} errors detected.'.format(
            total, len(args.input), total - updated, updated, len(errors)))

    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()