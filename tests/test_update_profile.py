import unittest

from update_profile import render, replace_section


class ProfileTests(unittest.TestCase):
    def test_public_counts_and_recent_projects(self):
        repositories = [
            {'name': 'A', 'html_url': 'https://github.com/u/A', 'description': 'First | project', 'stargazers_count': 3, 'fork': False, 'archived': False, 'pushed_at': '2026-01-02T00:00:00Z'},
            {'name': 'B', 'html_url': 'https://github.com/u/B', 'description': None, 'stargazers_count': 2, 'fork': True, 'archived': False, 'pushed_at': '2026-01-03T00:00:00Z'},
            {'name': 'C', 'html_url': 'https://github.com/u/C', 'description': None, 'stargazers_count': 1, 'fork': False, 'archived': True, 'pushed_at': '2026-01-01T00:00:00Z'},
        ]
        result = render({'public_repos': 3, 'followers': 7}, repositories)
        self.assertIn('3 repository pubbliche', result)
        self.assertIn('6 stelle', result)
        self.assertIn('7 follower', result)
        self.assertIn('First &#124; project', result)
        self.assertNotIn('[B]', result)
        self.assertNotIn('[C]', result)

    def test_replace_requires_unique_markers_and_preserves_surroundings(self):
        source = 'Before\n<!-- github-data:start -->\nold\n<!-- github-data:end -->\nAfter\n'
        self.assertEqual(replace_section(source, 'new'), 'Before\n<!-- github-data:start -->\nnew\n<!-- github-data:end -->\nAfter\n')
        with self.assertRaises(ValueError):
            replace_section('missing markers', 'new')


if __name__ == '__main__':
    unittest.main()
