# this package
from godot_project_parser.types import PackedStringArray


def test_packstringarray_repr():
	psa = PackedStringArray(["foo", "bar", "baz"])

	assert repr(psa) == "PackedStringArray(['foo', 'bar', 'baz'])"
