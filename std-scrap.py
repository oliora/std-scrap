from __future__ import print_function

from lxml import html
import re
import urlparse

import sys
import json


class Doc(object):
    def __init__(self, number, title, authors,
                 url=None, date=None, mailing_date=None,
                 prev_version=None, subgroups=None, disposition=None
                 ):
        self.number = number
        self.title = title
        self.authors = authors
        self.url = url
        self.date = date
        self.mailing_date = mailing_date
        self.prev_version = prev_version
        self.subgroups = subgroups
        self.disposition = disposition
        
#    def __str__(self):
#        return str(self.__dict__)
        
    def __repr__(self):
        return str(self.__dict__)
        

_subgroups_splitter = re.compile(r',|/|\\')
_doc_number_re = re.compile(r'(?:N\d+)|(?:SD-\d+)')
_j16_doc_number_ref_re = re.compile(r'(N\d+)(?:\s*=\s*\d{2}-\d{4})?')
_date_re = re.compile(r'(?:(\d{2}|\d{4})(?:--?|/)(\d{1,2})(?:(?:[-/])(\d{1,2}))?)')  # There is bug where date looks like YYYY--MM
_date2_re = re.compile(r'(\d{4})(\d{2})(\d{2})')  # YYYYMMDD


def parse_authors(e):
    authors = e.text
    return [] if authors is None else [s.strip() for s in authors.split(',')]


def parse_subgroups(e):
    subgroups = e.text
    return [] if subgroups is None else [s.strip() for s in _subgroups_splitter.split(subgroups)]
    
    
def parse_plain(e):
    txt = e.text
    return '' if txt is None else txt.strip()
    
    
def parse_doc_number(e):
    r = e.text_content().strip()
    if r and not _doc_number_re.match(r):
        raise ValueError('Bad document number: {0}'.format(r))
    return r
    
def parse_j16_doc_ref(e):
    txt = e.text_content().strip()
    if not txt:
        return ''
    m = _j16_doc_number_ref_re.match(txt)
    if not m:
        raise ValueError('Bad J16 document reference: {0}'.format(txt))
    return m.group(1)

    
def parse_doc_url(e):
    link = e.xpath('a/@href')
    return None if not link else urlparse.urljoin(e.base_url, link[0])


# TODO: parse disposition
def parse_disposition(e):
    return parse_plain(e)
    

def parse_date(e):
    txt = parse_plain(e)
    if not txt or txt.lower() == 'missing':
        return None
    m = _date_re.match(txt)
    if not m:
        m = _date2_re.match(txt)
        if not m:
            raise ValueError('Bad document date: {0}'.format(txt))
    year = int(m.group(1))
    if year <= 99:
        year += 2000
    if m.group(3):
        return "{0}-{1:02}-{2:02}".format(year, int(m.group(2)), int(m.group(3)))
    else:
        return "{0}-{1:02}".format(year, int(m.group(2)))


class ModernTableParser(object):
    """
    Modern table
    ------------
    In use since 2013

    Columns:
        'WG21 Number'
        'Title'
        'Author'
        'Document Date'
        'Mailing Date'
        'Previous Version'
        'Subgroup'
        'Disposition'
    """
    @classmethod
    def can_parse(cls, table):
        headers = table.xpath('tr[1]/th/text()|tbody/tr[1]/th/text()')
        return headers == ['WG21 Number', 'Title', 'Author', 'Document Date', 'Mailing Date',
                           'Previous Version', 'Subgroup', 'Disposition']

    def parse(self, table):
        self
        docs = []
        for r in table.xpath('tr|tbody/tr'):
            row = r.xpath('td')
            if not len(row):
                continue
            try:
                if len(row) != 8:
                    raise ValueError("Wrong number of columns")
                doc = Doc(number=parse_doc_number(row[0]),
                          title=parse_plain(row[1]),
                          authors=parse_authors(row[2]),
                          url=parse_doc_url(row[0]),
                          date=parse_date(row[3]),
                          mailing_date=parse_date(row[4]),
                          prev_version=parse_doc_number(row[5]),
                          subgroups=parse_subgroups(row[6]),
                          disposition=parse_disposition(row[7])
                          )
                docs.append(doc)
            except:
                pass
        return docs


class J16TransitionTableParser(object):
    """
    Transition between old J16 and modern tables
    ---------
    Was used since after 2011-02 till 2012(inclusive)

    Columns:
        'WG21 Number'
        'PL22.16 Number'
        'Title'
        'Author'
        'Document Date'
        'Mailing Date'
        'Previous Version'
        'Subgroup'
        'Disposition'
    """
    @classmethod
    def can_parse(cls, table):
        headers = table.xpath('tr[1]/th/text()|tbody/tr[1]/th/text()')
        return headers == ['WG21 Number', 'PL22.16 Number', 'Title', 'Author', 'Document Date', 'Mailing Date',
                           'Previous Version', 'Subgroup', 'Disposition']

    def parse(self, table):
        self
        docs = []
        for r in table.xpath('tr|tbody/tr'):
            row = r.xpath('td')
            if not len(row):
                continue
            try:
                if len(row) != 9:
                    raise ValueError("Wrong number of columns")
                doc = Doc(number=parse_doc_number(row[0]),
                          title=parse_plain(row[2]),
                          authors=parse_authors(row[3]),
                          url=parse_doc_url(row[0]),
                          date=parse_date(row[4]),
                          mailing_date=parse_date(row[5]),
                          prev_version=parse_j16_doc_ref(row[6]),
                          subgroups=parse_subgroups(row[7]),
                          disposition=parse_disposition(row[8])
                          )
                docs.append(doc)
            except:
                pass
        return docs        


class J16TableParser(object):
    """
    J16 table
    ---------
    Was used since 2004 till 2011-02 (inclusive)

    Columns:
        'WG21 Number'
        'J16 Number' or 'PL22.16 Number'
        'Title'
        'Author'
        'Document Date'
        'Mailing Date'
        'Previous Version'
        'Subgroup'
    """
    @classmethod
    def can_parse(cls, table):
        headers = table.xpath('tr[1]/th/text()|tbody/tr[1]/th/text()')
        return (headers == ['WG21 Number', 'J16 Number', 'Title', 'Author', 'Document Date', 'Mailing Date',
                            'Previous Version', 'Subgroup'] or
                headers == ['WG21 Number', 'PL22.16 Number', 'Title', 'Author', 'Document Date', 'Mailing Date',
                            'Previous Version', 'Subgroup'])

    def parse(self, table):
        docs = []
        for r in table.xpath('tr|tbody/tr'):
            row = r.xpath('td')
            if not len(row):
                continue
            try:
                if len(row) != 8:
                    raise ValueError("Wrong number of columns")
                doc = Doc(number=parse_doc_number(row[0]),
                          title=parse_plain(row[2]),
                          authors=parse_authors(row[3]),
                          url=parse_doc_url(row[0]),
                          date=parse_date(row[4]),
                          mailing_date=parse_date(row[5]),
                          prev_version=parse_j16_doc_ref(row[6]),
                          subgroups=parse_subgroups(row[7])
                          )
                docs.append(doc)
            except:
                pass
        return docs        
        

class Parser(object):
    class Context(object):
        last_table_parser = None

    __parsers = [ModernTableParser, J16TransitionTableParser, J16TableParser]
    
    def _find_table_parser(self, table, def_parser_cls=None):
        for p in self.__parsers:
            if p.can_parse(table):
                return p

        if not def_parser_cls:
            raise ValueError("Can not find compatible table parser and default one is not specified")
        return def_parser_cls

    def parse(self, url_or_file):
        doc = html.parse(url_or_file)

        doc_tables = doc.xpath('/html/body/table')
        
        if not doc_tables:
            raise ValueError("No one documents table found on page")
    
        ctx = self.Context()

        docs = []
        for t in doc_tables:
            docs += self.__parse_table(ctx, t)
        return docs
            
    def __parse_table(self, ctx, table):
        ctx.last_table_parser = self._find_table_parser(table, ctx.last_table_parser)
        return ctx.last_table_parser().parse(table)


def main():
    input_filename = sys.argv[1]
    docs = Parser().parse(input_filename)

    class MyEncoder(json.JSONEncoder):
        def default(self, o):
            return o.__dict__

    print(json.dumps(docs, indent=2, cls=MyEncoder))
    #print(json.dumps(docs, indent=2))


if __name__ == "__main__":
        main()