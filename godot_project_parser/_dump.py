#!/usr/bin/env python3
#
#  _dump.py
"""
Reconstruct a ``project.godot`` file.
"""
#
#  Copyright © 2025 Dominic Davis-Foster <dominic@davis-foster.co.uk>
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
import json
from typing import IO, Any, Dict, List, Mapping, Union

# this package
from godot_project_parser.types import GodotObject, PackedStringArray

__all__ = (
		"dump",
		"dump_dict",
		"dump_godot_object",
		"dump_list",
		"dump_packed_string_array",
		"dump_primitive",
		"dump_table",
		"dump_value",
		"dumps",
		)


def dump_table(table: Dict[str, Any]) -> str:
	buf = [f"{k}={dump_value(v)}" for k, v in table.items()]
	return '\n'.join(buf)


def dump_value(value: Any) -> str:
	if isinstance(value, (str, int, float)):
		return (dump_primitive(value))
	elif isinstance(value, PackedStringArray):
		return (dump_packed_string_array(value))
	elif isinstance(value, list):
		return (dump_list(value))
	elif isinstance(value, dict):
		return (dump_dict(value))
	elif isinstance(value, GodotObject):
		return (dump_godot_object(value))
	elif value is None:
		return "null"
	else:
		raise NotImplementedError(type(value))


def dump_godot_object(obj: GodotObject) -> str:
	return f"Object({obj.name},{dump_dict(obj.kwargs, oneline=True)[1:-1]})"


def dump_list(l: List) -> str:
	buf = ['[']
	for item in l[:-1]:
		buf.append(dump_value(item))
		buf.append("\n, ")

	if l:
		buf.append(dump_value(l[-1]))
		buf.append('\n')
	buf.append(']')
	return ''.join(buf)


def dump_dict(d: Dict[str, Any], oneline: bool = False) -> str:
	buf = ['{']
	if not oneline:
		buf.append('\n')

	dict_items = list(d.items())
	for key, value in dict_items[:-1]:
		buf.append(f"{json.dumps(key)}:")
		if not oneline:
			buf.append(' ')
		buf.append(f"{dump_value(value)},")
		if not oneline:
			buf.append('\n')

	if dict_items:
		key, value = dict_items[-1]
		buf.append(f"{json.dumps(key)}:")
		if not oneline:
			buf.append(' ')
		buf.append(f"{dump_value(value)}")
		if not oneline:
			buf.append('\n')

	buf.append('}')
	return ''.join(buf)


def dump_primitive(primitive: Union[str, float]) -> str:
	return json.dumps(primitive)


def dump_packed_string_array(psa: PackedStringArray) -> str:
	body = ", ".join([json.dumps(elem) for elem in psa])
	return f"PackedStringArray({body})"


header = """\
; Engine configuration file.
; It's best edited using the editor UI and not directly,
; since the parameters that go here are not all obvious.
;
; Format:
;   [section] ; section goes between []
;   param=value ; assign values to parameters
"""


def dumps(obj: Mapping[str, Any]) -> str:
	"""
	Reconstruct a ``project.godot`` file and return as a string.

	:param obj:
	"""

	buf = [header]
	for key, value in obj.items():

		if isinstance(value, (str, int, float)):
			buf.append(f"{key}={dump_primitive(value)}")
		elif isinstance(value, dict):
			buf.append(f"\n[{key}]\n")
			buf.append(dump_table(value))
		else:
			raise NotImplementedError(type(value))

	return '\n'.join(buf)


def dump(obj: Mapping[str, Any], fp: IO[bytes]) -> None:
	"""
	Reconstruct a ``project.godot`` file and write to the given file.

	:param obj:
	:param fp:
	"""

	fp.write(dumps(obj).encode("UTF-8"))
