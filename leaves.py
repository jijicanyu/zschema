import unittest
import re
import dateutil.parser

from keys import *

class DataValidationException(TypeError):
	pass


VALID_ES_INDEX_TYPES = [
	"analyzed", # full-text
	"not_analyzed", # searchable, not full-text,
	"no", # field is not searchable
]


VALID_ES_ANALYZERS = [
	"standard",   # The standard analyzer is the default analyzer that Elasticsearch uses.
				  # It is the best general choice for analyzing text that may be in any language. 
				  # It splits the text on word boundaries, as defined by the Unicode Consortium, 
				  # and removes most punctuation.
	"simple",     # The simple analyzer splits the text on anything that isn't a letter, 
				  # and lowercases the terms. It would produce
	"whitespace", # The whitespace analyzer splits the text on whitespace. It doesn't lowercase.
]


class Leaf(Keyable):
		
	def to_es(self, name):
		pass
		
	def to_bigquery(self, name):
		mode = "REQUIRED" if self.required else "NULLABLE"
		return {"name":self.key_to_bq(name), "type":self.BQ_TYPE, "mode":mode}

	def to_string(self, name):
		return "%s: %s" % (self.key_to_string(name), self.__class__.__name__.lower())
		
	def print_indent_string(self, name, indent):
		val = self.key_to_string(name)
		if indent:
			tabs = "\t" * indent
			val = tabs + val
		print val
		
	def validate(self, name, value):
		if type(value) not in self.EXPECTED_CLASS:
			raise DataValidationException("class mismatch for %s: expected %s, %s has class %s",
					self.key_to_string(name), self.EXPECTED_CLASS, 
					str(value), value.__class__.__name__)
		if hasattr(self, "_validate"):
			self._validate(key_to_string(name), value)
			
	def __init__(self, required=False):
		self.required = required


class AnalyzedString(Leaf):
	ES_TYPE = "string"
	BQ_TYPE = "STRING"
	ES_INDEX_TYPE = "analyzed"
	EXPECTED_CLASS = [str,]
	
	INVALID = 23
	VALID = "asdf"


class String(Leaf):
	ES_TYPE = "string"
	BQ_TYPE = "STRING"
	ES_INDEX_TYPE = "not_analyzed"
	EXPECTED_CLASS = [str,]

	INVALID = 23
	VALID = "asdf"


class IPv4Address(Leaf):
	ES_TYPE = "ip"
	BQ_TYPE = "STRING"
	EXPECTED_CLASS = [str,]
	IP_REGEX = re.compile('(\d{1,3}\.){3}\d{1,3}')
	
	def _is_ipv4_addr(self, ip):
		return bool(self.IP_REGEX.match(ip))
	
	def _validate(self, name, value):
		if not self._is_ipv4_addr(value):
			raise DataValidationException("%s: the value %s is not a valid IPv4 address",
					name, value)
		
	INVALID = "my string"
	VALID = "141.212.120.0"


class Integer(Leaf):
	ES_TYPE = "integer"
	BQ_TYPE = "INTEGER"
	EXPECTED_CLASS = [int,]
	
	INVALID = 8589934592
	VALID = 234234252
	
	BITS = 32

	def _validate(self, name, value):
		max_ = 2**self.BITS - 1
		min_ = -2**self.BITS + 1
		if value > max_:
			raise DataValidationException("%s: %s is larger than max (%s)",
					name, str(value), str(max_))
		if value < min_:
			raise DataValidationException("%s: %s is smaller than min (%s)",
					name, str(value), str(min_))


class Byte(Integer):
	ES_TYPE = "byte"
	BITS = 8
	INVALID = 2**8+5
	VALID = 34


class Short(Integer):
	ES_TYPE = "short"
	BITS = 16
	INVALID = 2**16
	VALID = 0xFFFF


class Long(Integer):
	ES_TYPE = "long"
	BQ_TYPE = "DOUBLE"
	EXPECTED_CLASS = [int,long]
	INVALID = 2l**68
	VALID = 10l
	BITS = 64
	

class Float(Leaf):
	ES_TYPE = "float"
	BQ_TYPE = "DOUBLE"
	EXPECTED_CLASS = [float,]
	INVALID = "I'm a string!"
	VALID = 10.0
	

class Double(Float):
	ES_TYPE = "double"
	BQ_TYPE = "DOUBLE"


class Boolean(Leaf):
	ES_TYPE = "boolean"
	BQ_TYPE = "BOOLEAN"
	EXPECTED_CLASS = [bool,]
	INVALID = 0
	VALID = True


class Binary(Leaf):
	ES_TYPE = "binary"
	BQ_TYPE = "STRING"
	ES_INDEX_TYPE = "no"
	EXPECTED_CLASS = [str,]
	B64_REGEX = re.compile('[A-Fa-f0-9]+')
	
	def _is_base64(self, data):
		return bool(self.B64_REGEX.match(data))
	
	def _validate(self, name, value):
		if not self._is_base64(value):
			raise DataValidationException("%s: the value %s is not valid Base64",
					name, value)

	VALID = "03F87824"
	INVALID = "normal"
	

class IndexedBinary(Binary):
	ES_TYPE = "binary"
	BQ_TYPE = "STRING"
	ES_INDEX_TYPE = "not_analyzed"


class DateTime(Leaf):
	ES_TYPE = "datetime"
	BQ_TYPE = "TIMESTAMP"
	EXPECTED_CLASS = [str, int]
	
	VALID = "Wed Jul  8 08:52:01 EDT 2015"
	INVALID = "Wed DNE  35 08:52:01 EDT 2015"
	
	def _validate(self, name, value):
		try:
			dateutil.parser.parse(value)
		except Exception, e:
			raise DataValidationException("%s: %s is not valid timestamp",
					name, str(value))


VALID_LEAVES = [
	DateTime,
	AnalyzedString,
	String,
	Binary,
	IndexedBinary,
	Boolean,
	Double,
	Float,
	Long,
	Short,
	Byte,
	Integer,
	IPv4Address
]


class LeafUnitTests(unittest.TestCase):
	def test_valid(self):
		for leaf in VALID_LEAVES:
			leaf().validate(leaf.__name__, leaf.VALID)

	def test_invalid(self):
		for leaf in VALID_LEAVES:
			try:
				leaf().validate(leaf.__name__, leaf.INVALID)
				raise Exception("invalid value did not fail for %s",
						leaf.__name__)
			except DataValidationException:
				continue
			

if __name__ == "__main__":
	unittest.main() 