from lxml import html
import re
import sys
import json


class Doc:
  def __init__(self, number, title, authors,
      url=None, date=None, mailing_date=None,
      prev_version=None, subgroups=None, disposition=None):
    self.number = number
    self.title = title
    self.authors = authors
    self.url = url
    self.date = date
    self.mailing_date = mailing_date
    self.prev_version = prev_version
    self.subgroups = subgroups
    self.disposition = disposition
    
#  def __str__(self):
#    return str(self.__dict__)
    
  def __repr__(self):
    return str(self.__dict__)
    

_subgroups_splitter = re.compile(r',|/|\\')    


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
  return e.text_content().strip()

  
def parse_doc_url(e):
  link = e.xpath('a/@href')
  return None if not link else link[0]


class ModernTableParser:
  """
  Modern table:
    WG21 Number,Title,Author,Document,Date,Mailing Date,Previous Version,Subgroup,Disposition
  """
  @classmethod
  def can_parse(cls, table):
    headers = table.xpath('tr[1]/th/text()|tbody/tr[1]/th/text()')
    return headers == ['WG21 Number','Title','Author','Document Date','Mailing Date','Previous Version','Subgroup','Disposition']

  def parse(self, table):
    docs = []
    for r in table.xpath('tr|tbody/tr'):
      row = r.xpath('td')
      if not len(row):
        continue
      doc = Doc(number=parse_doc_number(row[0]),
          title=parse_plain(row[1]),
          authors=parse_authors(row[2]),
          url=parse_doc_url(row[0]),
          date=parse_plain(row[3]),
          mailing_date=parse_plain(row[4]),
          prev_version=parse_doc_number(row[5]),
          subgroups=parse_subgroups(row[6]),
          disposition=parse_plain(row[7])  # TODO: decompose disposition 
        )
      docs.append(doc)
    return docs


def find_table_parser(table, def_parser_cls=None):
  if ModernTableParser.can_parse(table):
    return ModernTableParser

  if not def_parser_cls:
    raise ValueError("Can not find compatible table parser and default one is not specified")
  return def_parser_cls


class Parser:
  class Context:
    last_table_parser = None
    
  __ctx = None
  
  def parse(self, url_or_file):
    doc = html.parse(url_or_file)

    dtables = doc.xpath('/html/body/table')
    
    if not dtables:
      raise ValueError("No one documents table found on page")
  
    ctx = Parser.Context()

    docs = []
    for t in dtables:
      docs += self.__parse_table(ctx, t)
    return docs
      
  def __parse_table(self, ctx, table):
    ctx.last_table_parser = find_table_parser(table, ctx.last_table_parser)
    return ctx.last_table_parser().parse(table)


def main():
  input_filename = sys.argv[1]
  docs = Parser().parse(input_filename)

  class MyEncoder(json.JSONEncoder):
    def default(self, o):
      return o.__dict__

  print json.dumps(docs, indent=2, cls=MyEncoder)


if __name__ == "__main__":
    main()