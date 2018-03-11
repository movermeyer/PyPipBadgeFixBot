import unittest

from pypip_dot_in_helpers import pypip_in_to_shields_io, replace_in_readme


class TestPyPipMigration(unittest.TestCase):
    def test_regular_url(self):
        provided = "https://pypip.in/py_versions/fbadmin/badge.svg"
        expected = "https://img.shields.io/pypi/pyversions/fbadmin.svg"
        self.assertEqual(pypip_in_to_shields_io(provided), expected)

    def test_with_style(self):
        provided = "https://pypip.in/py_versions/fbadmin/badge.svg?style=flat"
        expected = "https://img.shields.io/pypi/pyversions/fbadmin.svg?style=flat"
        self.assertEqual(pypip_in_to_shields_io(provided), expected)

    def test_with_text(self):
        provided = "https://pypip.in/py_versions/fbadmin/badge.svg?text=Hello"
        expected = "https://img.shields.io/pypi/pyversions/fbadmin.svg?label=Hello"
        self.assertEqual(pypip_in_to_shields_io(provided), expected)

    def test_with_period(self):
        provided = "https://pypip.in/d/fbadmin/badge.svg?period=day"
        expected = "https://img.shields.io/pypi/dd/fbadmin.svg"
        self.assertEqual(pypip_in_to_shields_io(provided), expected)

    def test_markdown_links(self):
        provided = "[![Version](https://pypip.in/v/epyper/badge.png)](https://pypi.python.org/pypi/epyper)"
        expected = "[![Version](https://img.shields.io/pypi/v/epyper.svg)](https://pypi.python.org/pypi/epyper)"
        self.assertEqual(replace_in_readme(provided)[0], expected)


if __name__ == '__main__':
    unittest.main()
