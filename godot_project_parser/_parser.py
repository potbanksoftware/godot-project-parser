#!/usr/bin/env python3
#
#  _parser.py
"""
Internal tomli-based parser.
"""
#
#  From https://github.com/hukkin/tomli/blob/master/src/tomli/_parser.py
#
#  Copyright © 2021 Taneli Hukkinen
#  Changes Copyright © 2025 Dominic Davis-Foster <dominic@davis-foster.co.uk>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#  OR OTHER DEALINGS IN THE SOFTWARE.
#

# stdlib
from typing import IO, Any, Dict, Final, List, Optional, Tuple

# 3rd party
from tomli._parser import (
		ILLEGAL_BASIC_STR_CHARS,
		ILLEGAL_COMMENT_CHARS,
		ILLEGAL_LITERAL_STR_CHARS,
		ILLEGAL_MULTILINE_BASIC_STR_CHARS,
		MAX_INLINE_NESTING,
		TOML_WS,
		TOML_WS_AND_NEWLINE,
		Flags,
		NestedDict,
		TOMLDecodeError,
		make_safe_parse_float,
		parse_basic_str_escape,
		parse_multiline_str,
		skip_chars,
		skip_until
		)
from tomli._re import RE_DATETIME, RE_LOCALTIME, RE_NUMBER, match_to_datetime, match_to_localtime, match_to_number
from tomli._types import Key, ParseFloat, Pos

# this package
from godot_project_parser.types import GodotObject, PackedStringArray

__all__ = [
		"Output",
		"create_dict_rule",
		"create_list_rule",
		"key_value_rule",
		"load",
		"loads",
		"parse_array",
		"parse_basic_str",
		"parse_basic_str_escape_multiline",
		"parse_inline_table",
		"parse_key",
		"parse_key_part",
		"parse_key_value_pair",
		"parse_literal_str",
		"parse_object",
		"parse_one_line_basic_str",
		"parse_packed_string_array",
		"parse_value",
		"skip_comment",
		"skip_comments_and_array_ws"
		]

BARE_KEY_CHARS: Final = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/.")
KEY_INITIAL_CHARS: Final = BARE_KEY_CHARS | frozenset("\"'")


def load(__fp: IO[bytes], *, parse_float: ParseFloat = float) -> Dict[str, Any]:
	"""
	Parse ``project.godot`` from a binary file object.

	:param __fp:
	:param parse_float:
	"""

	b = __fp.read()
	try:
		s = b.decode()
	except AttributeError:
		raise TypeError("File must be opened in binary mode, e.g. use `open('foo.toml', 'rb')`") from None
	return loads(s, parse_float=parse_float)


def loads(__s: str, *, parse_float: ParseFloat = float) -> Dict[str, Any]:
	"""
	Parse ``project.godot`` from a string.

	:param __s:
	:param parse_float:
	"""

	# The spec allows converting "\r\n" to "\n", even in string
	# literals. Let's do so to simplify parsing.
	try:
		src = __s.replace("\r\n", '\n')
	except (AttributeError, TypeError):
		raise TypeError(f"Expected str object, not '{type(__s).__qualname__}'") from None
	pos = 0
	out = Output()
	header: Key = ()
	parse_float = make_safe_parse_float(parse_float)

	# Parse one statement at a time
	# (typically means one line in TOML source)
	while True:
		# 1. Skip line leading whitespace
		pos = skip_chars(src, pos, TOML_WS)

		# 2. Parse rules. Expect one of the following:
		#    - end of file
		#    - end of line
		#    - comment
		#    - key/value pair
		#    - append dict to list (and move to its namespace)
		#    - create dict (and move to its namespace)
		# Skip trailing whitespace when applicable.
		try:
			char = src[pos]
		except IndexError:
			break
		if char == '\n':
			pos += 1
			continue
		if char in KEY_INITIAL_CHARS:
			pos = key_value_rule(src, pos, out, header, parse_float)
			pos = skip_chars(src, pos, TOML_WS)
		elif char == '[':
			try:
				second_char: Optional[str] = src[pos + 1]
			except IndexError:
				second_char = None
			out.flags.finalize_pending()
			if second_char == '[':
				pos, header = create_list_rule(src, pos, out)
			else:
				pos, header = create_dict_rule(src, pos, out)
			pos = skip_chars(src, pos, TOML_WS)
		elif char not in "#;":
			raise TOMLDecodeError("Invalid statement", src, pos)

		# 3. Skip comment
		pos = skip_comment(src, pos)

		# 4. Expect end of line or end of file
		try:
			char = src[pos]
		except IndexError:
			break
		if char != '\n':
			raise TOMLDecodeError("Expected newline or end of document after a statement", src, pos)
		pos += 1

	return out.data.dict


class Output:

	def __init__(self) -> None:
		self.data = NestedDict()
		self.flags = Flags()


def skip_comment(src: str, pos: Pos) -> Pos:
	try:
		char: str = src[pos]
	except IndexError:
		return pos

	if char in "#;":
		return skip_until(src, pos + 1, '\n', error_on=ILLEGAL_COMMENT_CHARS, error_on_eof=False)
	return pos


def skip_comments_and_array_ws(src: str, pos: Pos) -> Pos:
	while True:
		pos_before_skip = pos
		pos = skip_chars(src, pos, TOML_WS_AND_NEWLINE)
		pos = skip_comment(src, pos)
		if pos == pos_before_skip:
			return pos


def create_dict_rule(src: str, pos: Pos, out: Output) -> Tuple[Pos, Key]:
	pos += 1  # Skip "["
	pos = skip_chars(src, pos, TOML_WS)
	pos, key = parse_key(src, pos)

	if out.flags.is_(key, Flags.EXPLICIT_NEST) or out.flags.is_(key, Flags.FROZEN):
		raise TOMLDecodeError(f"Cannot declare {key} twice", src, pos)
	out.flags.set(key, Flags.EXPLICIT_NEST, recursive=False)
	try:
		out.data.get_or_create_nest(key)
	except KeyError:
		raise TOMLDecodeError("Cannot overwrite a value", src, pos) from None

	if not src.startswith(']', pos):
		raise TOMLDecodeError("Expected ']' at the end of a table declaration", src, pos)
	return pos + 1, key


def create_list_rule(src: str, pos: Pos, out: Output) -> Tuple[Pos, Key]:
	pos += 2  # Skip "[["
	pos = skip_chars(src, pos, TOML_WS)
	pos, key = parse_key(src, pos)

	if out.flags.is_(key, Flags.FROZEN):
		raise TOMLDecodeError(f"Cannot mutate immutable namespace {key}", src, pos)
	# Free the namespace now that it points to another empty list item...
	out.flags.unset_all(key)
	# ...but this key precisely is still prohibited from table declaration
	out.flags.set(key, Flags.EXPLICIT_NEST, recursive=False)
	try:
		out.data.append_nest_to_list(key)
	except KeyError:
		raise TOMLDecodeError("Cannot overwrite a value", src, pos) from None

	if not src.startswith("]]", pos):
		raise TOMLDecodeError("Expected ']]' at the end of an array declaration", src, pos)
	return pos + 2, key


def key_value_rule(src: str, pos: Pos, out: Output, header: Key, parse_float: ParseFloat) -> Pos:
	pos, key, value = parse_key_value_pair(src, pos, parse_float, nest_lvl=0)
	key_parent, key_stem = key[:-1], key[-1]
	abs_key_parent = header + key_parent

	relative_path_cont_keys = (header + key[:i] for i in range(1, len(key)))
	for cont_key in relative_path_cont_keys:
		# Check that dotted key syntax does not redefine an existing table
		if out.flags.is_(cont_key, Flags.EXPLICIT_NEST):
			raise TOMLDecodeError(f"Cannot redefine namespace {cont_key}", src, pos)
		# Containers in the relative path can't be opened with the table syntax or
		# dotted key/value syntax in following table sections.
		out.flags.add_pending(cont_key, Flags.EXPLICIT_NEST)

	if out.flags.is_(abs_key_parent, Flags.FROZEN):
		raise TOMLDecodeError(f"Cannot mutate immutable namespace {abs_key_parent}", src, pos)

	try:
		nest = out.data.get_or_create_nest(abs_key_parent)
	except KeyError:
		raise TOMLDecodeError("Cannot overwrite a value", src, pos) from None
	if key_stem in nest:
		raise TOMLDecodeError("Cannot overwrite a value", src, pos)
	# Mark inline table and array namespaces recursively immutable
	if isinstance(value, (dict, list)):
		out.flags.set(header + key, Flags.FROZEN, recursive=True)
	nest[key_stem] = value
	return pos


def parse_key_value_pair(src: str, pos: Pos, parse_float: ParseFloat, nest_lvl: int) -> Tuple[Pos, Key, Any]:
	pos, key = parse_key(src, pos)
	try:
		char: Optional[str] = src[pos]
	except IndexError:
		char = None
	if char is None or char not in "=:":
		raise TOMLDecodeError("Expected '=' or ':' after a key in a key/value pair", src, pos)
	pos += 1
	pos = skip_chars(src, pos, TOML_WS)
	pos, value = parse_value(src, pos, parse_float, nest_lvl)
	return pos, key, value


def parse_key(src: str, pos: Pos) -> Tuple[Pos, Key]:
	pos, key_part = parse_key_part(src, pos)
	key: Key = (key_part, )
	pos = skip_chars(src, pos, TOML_WS)
	while True:
		try:
			char: Optional[str] = src[pos]
		except IndexError:
			char = None
		if char != '.':
			return pos, key
		pos += 1
		pos = skip_chars(src, pos, TOML_WS)
		pos, key_part = parse_key_part(src, pos)
		key += (key_part, )
		pos = skip_chars(src, pos, TOML_WS)


def parse_key_part(src: str, pos: Pos) -> Tuple[Pos, str]:
	try:
		char: Optional[str] = src[pos]
	except IndexError:
		char = None
	if char in BARE_KEY_CHARS:
		start_pos = pos
		pos = skip_chars(src, pos, BARE_KEY_CHARS)
		return pos, src[start_pos:pos]
	if char == "'":
		return parse_literal_str(src, pos)
	if char == '"':
		return parse_one_line_basic_str(src, pos)
	raise TOMLDecodeError("Invalid initial character for a key part", src, pos)


def parse_one_line_basic_str(src: str, pos: Pos) -> Tuple[Pos, str]:
	pos += 1
	return parse_basic_str(src, pos, multiline=False)


def parse_array(src: str, pos: Pos, parse_float: ParseFloat, nest_lvl: int) -> Tuple[Pos, List[Any]]:
	pos += 1
	array: List[Any] = []

	pos = skip_comments_and_array_ws(src, pos)
	if src.startswith(']', pos):
		return pos + 1, array
	while True:
		pos, val = parse_value(src, pos, parse_float, nest_lvl)
		array.append(val)
		pos = skip_comments_and_array_ws(src, pos)

		c = src[pos:pos + 1]
		if c == ']':
			return pos + 1, array
		if c != ',':
			raise TOMLDecodeError("Unclosed array", src, pos)
		pos += 1

		pos = skip_comments_and_array_ws(src, pos)
		if src.startswith(']', pos):
			return pos + 1, array


def parse_inline_table(src: str, pos: Pos, parse_float: ParseFloat, nest_lvl: int) -> Tuple[Pos, Dict[str, Any]]:
	pos += 1
	nested_dict = NestedDict()
	flags = Flags()

	pos = skip_chars(src, pos, TOML_WS)
	if src.startswith('}', pos):
		return pos + 1, nested_dict.dict
	while True:
		pos = skip_chars(src, pos, '\n')
		pos, key, value = parse_key_value_pair(src, pos, parse_float, nest_lvl)
		key_parent, key_stem = key[:-1], key[-1]
		if flags.is_(key, Flags.FROZEN):
			raise TOMLDecodeError(f"Cannot mutate immutable namespace {key}", src, pos)
		try:
			nest = nested_dict.get_or_create_nest(key_parent, access_lists=False)
		except KeyError:
			raise TOMLDecodeError("Cannot overwrite a value", src, pos) from None
		if key_stem in nest:
			raise TOMLDecodeError(f"Duplicate inline table key {key_stem!r}", src, pos)
		nest[key_stem] = value
		pos = skip_chars(src, pos, TOML_WS)
		pos = skip_chars(src, pos, '\n')
		c = src[pos:pos + 1]
		if c == '}':
			return pos + 1, nested_dict.dict
		if c != ',':
			raise TOMLDecodeError("Unclosed inline table", src, pos)
		if isinstance(value, (dict, list)):
			flags.set(key, Flags.FROZEN, recursive=True)
		pos += 1
		pos = skip_chars(src, pos, TOML_WS)


def parse_basic_str_escape_multiline(src: str, pos: Pos) -> Tuple[Pos, str]:
	return parse_basic_str_escape(src, pos, multiline=True)


def parse_literal_str(src: str, pos: Pos) -> Tuple[Pos, str]:
	pos += 1  # Skip starting apostrophe
	start_pos = pos
	pos = skip_until(src, pos, "'", error_on=ILLEGAL_LITERAL_STR_CHARS, error_on_eof=True)
	return pos + 1, src[start_pos:pos]  # Skip ending apostrophe


## Can there be multiline strings?
# def parse_multiline_str(src: str, pos: Pos, *, literal: bool) -> Tuple[Pos, str]:
# 	pos += 3
# 	if src.startswith('\n', pos):
# 		pos += 1

# 	if literal:
# 		delim = "'"
# 		end_pos = skip_until(
# 				src,
# 				pos,
# 				"'''",
# 				error_on=ILLEGAL_MULTILINE_LITERAL_STR_CHARS,
# 				error_on_eof=True,
# 				)
# 		result = src[pos:end_pos]
# 		pos = end_pos + 3
# 	else:
# 		delim = '"'
# 		pos, result = parse_basic_str(src, pos, multiline=True)

# 	# Add at maximum two extra apostrophes/quotes if the end sequence
# 	# is 4 or 5 chars long instead of just 3.
# 	if not src.startswith(delim, pos):
# 		return pos, result
# 	pos += 1
# 	if not src.startswith(delim, pos):
# 		return pos, result + delim
# 	pos += 1
# 	return pos, result + (delim * 2)


def parse_basic_str(src: str, pos: Pos, *, multiline: bool) -> Tuple[Pos, str]:
	if multiline:
		error_on = ILLEGAL_MULTILINE_BASIC_STR_CHARS
		parse_escapes = parse_basic_str_escape_multiline
	else:
		error_on = ILLEGAL_BASIC_STR_CHARS
		parse_escapes = parse_basic_str_escape
	result = ''
	start_pos = pos
	while True:
		try:
			char = src[pos]
		except IndexError:
			raise TOMLDecodeError("Unterminated string", src, pos) from None
		if char == '"':
			if not multiline:
				return pos + 1, result + src[start_pos:pos]
			if src.startswith('"""', pos):
				return pos + 3, result + src[start_pos:pos]
			pos += 1
			continue
		if char == '\\':
			result += src[start_pos:pos]
			pos, parsed_escape = parse_escapes(src, pos)
			result += parsed_escape
			start_pos = pos
			continue
		if char in error_on:
			raise TOMLDecodeError(f"Illegal character {char!r}", src, pos)
		pos += 1


def parse_value(src: str, pos: Pos, parse_float: ParseFloat, nest_lvl: int) -> Tuple[Pos, Any]:
	if nest_lvl > MAX_INLINE_NESTING:
		# Pure Python should have raised RecursionError already.
		# This ensures mypyc binaries eventually do the same.
		raise RecursionError(  # pragma: no cover
			"TOML inline arrays/tables are nested more than the allowed"
			f" {MAX_INLINE_NESTING} levels"
		)

	try:
		char: Optional[str] = src[pos]
	except IndexError:
		char = None

	# IMPORTANT: order conditions based on speed of checking and likelihood

	# Basic strings
	if char == '"':
		if src.startswith('"""', pos):
			return parse_multiline_str(src, pos, literal=False)
		return parse_one_line_basic_str(src, pos)

	# Literal strings
	if char == "'":
		if src.startswith("'''", pos):
			return parse_multiline_str(src, pos, literal=True)
		return parse_literal_str(src, pos)

	# Booleans
	if char == 't':
		if src.startswith("true", pos):
			return pos + 4, True
	if char == 'f':
		if src.startswith("false", pos):
			return pos + 5, False

	if char == 'P':
		if src.startswith("PackedStringArray", pos):
			return parse_packed_string_array(src, pos, parse_float, nest_lvl=nest_lvl)

	if char == 'O':
		if src.startswith("Object", pos):
			return parse_object(src, pos, parse_float, nest_lvl=nest_lvl)

	if char == 'n':
		if src.startswith("null", pos):
			return pos + 4, None

	# Arrays
	if char == '[':
		return parse_array(src, pos, parse_float, nest_lvl + 1)

	# Inline tables
	if char == '{':
		return parse_inline_table(src, pos, parse_float, nest_lvl + 1)

	# Dates and times
	datetime_match = RE_DATETIME.match(src, pos)
	if datetime_match:
		try:
			datetime_obj = match_to_datetime(datetime_match)
		except ValueError as e:
			raise TOMLDecodeError("Invalid date or datetime", src, pos) from e
		return datetime_match.end(), datetime_obj
	localtime_match = RE_LOCALTIME.match(src, pos)
	if localtime_match:
		return localtime_match.end(), match_to_localtime(localtime_match)

	# Integers and "normal" floats.
	# The regex will greedily match any type starting with a decimal
	# char, so needs to be located after handling of dates and times.
	number_match = RE_NUMBER.match(src, pos)
	if number_match:
		return number_match.end(), match_to_number(number_match, parse_float)

	# Special floats
	first_three = src[pos:pos + 3]
	if first_three in {"inf", "nan"}:
		return pos + 3, parse_float(first_three)
	first_four = src[pos:pos + 4]
	if first_four in {"-inf", "+inf", "-nan", "+nan"}:
		return pos + 4, parse_float(first_four)

	raise TOMLDecodeError("Invalid value", src, pos)


def parse_packed_string_array(
		src: str,
		pos: Pos,
		parse_float: ParseFloat,
		nest_lvl: int,
		) -> Tuple[Pos, PackedStringArray]:
	pos += len("PackedStringArray")  # Skip 'PackedStringArray'
	pos += 1  # Skip '('

	array: List[str] = []

	while True:
		pos, val = parse_value(src, pos, parse_float, nest_lvl=nest_lvl)
		array.append(val)
		pos = skip_comments_and_array_ws(src, pos)

		c = src[pos:pos + 1]
		if c == ')':
			return pos + 1, PackedStringArray(array)
		if c != ',':
			raise TOMLDecodeError("Unclosed PackedStringArray", src, pos)
		pos += 1

		pos = skip_comments_and_array_ws(src, pos)
		if src.startswith(')', pos):
			return pos + 1, PackedStringArray(array)


def parse_object(src: str, pos: Pos, parse_float: ParseFloat, nest_lvl: int) -> Tuple[Pos, GodotObject]:
	pos += len("Object")  # Skip 'Object'
	pos += 1  # Skip '('
	start_pos = pos

	pos = skip_until(src, pos, ',', error_on=ILLEGAL_LITERAL_STR_CHARS, error_on_eof=True)

	object_name = src[start_pos:pos]
	pos += 1  # Skip comma

	nested_dict = NestedDict()
	flags = Flags()

	pos = skip_chars(src, pos, TOML_WS)
	if src.startswith(')', pos):
		return pos + 1, GodotObject(object_name, nested_dict.dict)
	while True:
		pos, key, value = parse_key_value_pair(src, pos, parse_float, nest_lvl=nest_lvl)
		key_parent, key_stem = key[:-1], key[-1]
		if flags.is_(key, Flags.FROZEN):
			raise TOMLDecodeError(f"Cannot mutate immutable namespace {key}", src, pos)
		try:
			nest = nested_dict.get_or_create_nest(key_parent, access_lists=False)
		except KeyError:
			raise TOMLDecodeError("Cannot overwrite a value", src, pos) from None
		if key_stem in nest:
			raise TOMLDecodeError(f"Duplicate Object key {key_stem!r}", src, pos)
		nest[key_stem] = value
		pos = skip_chars(src, pos, TOML_WS)
		c = src[pos:pos + 1]
		if c == ')':
			return pos + 1, GodotObject(object_name, nested_dict.dict)
		if c != ',':
			raise TOMLDecodeError("Unclosed Object", src, pos)
		if isinstance(value, (dict, list)):
			flags.set(key, Flags.FROZEN, recursive=True)
		pos += 1
		pos = skip_chars(src, pos, TOML_WS)
