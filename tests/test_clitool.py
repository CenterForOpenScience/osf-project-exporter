import datetime
from unittest import TestCase
import os
import shutil
import json
import pdb  # Use pdb.set_trace() to help with debugging
import traceback
from unittest.mock import patch

from click.testing import CliRunner
from pypdf import PdfReader

from osfexport.exporter import (
    call_api,
    get_project_data,
    explore_file_tree,
    explore_wikis,
    write_pdf,
    is_public,
    extract_project_id
)
from osfexport.cli import (
    cli, prompt_pat
)

TEST_PDF_FOLDER = 'good-pdfs'
TEST_INPUT = 'test_pdf.pdf'
FOLDER_OUT = os.path.join('tests', 'outfolder')

# Run tests in docker container
# with 'python -m unittest <tests.test_clitool.TESTCLASS>'


class TestAPI(TestCase):
    """Tests for interacting with the OSF API."""

    API_HOST = 'https://api.test.osf.io/v2'

    def test_basic_api_call_works(self):
        """Test for if JSON for user's projects are loaded correctly"""

        data = call_api(
            f'{TestAPI.API_HOST}/users/me/nodes/',
            os.getenv('TEST_PAT', '')
        )
        assert data.status == 200

        data = json.loads(data.read())
        assert isinstance(data, dict)
        # All mocked data assumes API version 2.20 is used
        assert data['meta']['version'] == '2.20', (
            'Expected API version 2.20, actual version: ',
            data['meta']['version']
        )

    def test_call_api_no_pat(self):
        public_node_id = json.loads(
            call_api(
                f'{TestAPI.API_HOST}/nodes', pat='',
                per_page=1
            ).read()
        )['data'][0]['id']

        result = call_api(
            f'{TestAPI.API_HOST}/nodes/{public_node_id}/', pat='',
        )
        assert result.status == 200

    def test_parse_single_project_json_as_expected(self):
        # Use first public project available for this test
        # TODO: allow choosing individual components to start export from
        # Currently a component will break this test
        data = call_api(
            f'{TestAPI.API_HOST}/nodes/',
            os.getenv('TEST_PAT', ''),
            per_page=1,
            filters={
                'parent': ''
            }
        )
        node = json.loads(data.read())['data'][0]
        id = extract_project_id(node['links']['html'])
        projects, root_projects = get_project_data(
            os.getenv('TEST_PAT', ''), dryrun=False,
            usetest=True, project_id=id
        )

        expected_child_count = len(
            json.loads(
                call_api(
                    f'{TestAPI.API_HOST}/nodes/{node["id"]}/children/',
                    os.getenv('TEST_PAT', '')
                ).read()
            )['data']
        )
        assert len(projects) == expected_child_count + 1
        assert len(root_projects) == 1, (root_projects)
        assert projects[0]['metadata']['title'] == node['attributes']['title']

    def test_filter_by_api(self):
        """Test if we use query params in API calls."""

        filters = {
            'category': '',
            'title': 'ttt',
        }
        data = call_api(
            f'{TestAPI.API_HOST}/nodes/',
            os.getenv('TEST_PAT', ''),
            per_page=12, filters=filters
        )
        assert data.status == 200

    def test_explore_api_file_tree(self):
        """Test using API to filter and search file links."""

        data = call_api(
            f'{TestAPI.API_HOST}/users/me/nodes/',
            os.getenv('TEST_PAT', '')
        )
        nodes = json.loads(data.read())['data']
        if len(nodes) > 0:
            node_id = nodes[0]['id']
            link = f'{TestAPI.API_HOST}/nodes/{node_id}/files/osfstorage/'
            files = explore_file_tree(
                link, os.getenv('TEST_PAT', ''), dryrun=False
            )
            assert isinstance(files, list)
        else:
            print("No nodes available, consider making a test project.")

    def test_export_projects_command(self):
        """Test we can successfully pull projects using the OSF API"""

        if os.path.exists(FOLDER_OUT):
            shutil.rmtree(FOLDER_OUT)
        os.mkdir(FOLDER_OUT)

        runner = CliRunner()

        # No PAT given - exception
        result = runner.invoke(
            cli, ['export-projects'], input='', terminal_width=60
        )
        assert result.exception

        # Use PAT to find user projects
        result = runner.invoke(
            cli, [
                'export-projects',
                '--folder', FOLDER_OUT,
                '--usetest'
            ],
            input=os.getenv('TEST_PAT', ''),
            terminal_width=60
        )
        assert not result.exception, (
            result.exc_info,
            traceback.format_tb(result.exc_info[2])
        )

    def test_get_public_status_on_code(self):
        assert not is_public(f'{TestAPI.API_HOST}/users/me')
        assert is_public(f'{TestAPI.API_HOST}')


class TestExporter(TestCase):
    """Tests for the exporter without real API usage."""

    def test_explore_mock_file_tree(self):
        """Test exploration of mock file tree."""

        files = explore_file_tree(
            'root', os.getenv('TEST_PAT', ''), dryrun=True
        )

        assert '/helloworld.txt.txt' == files[4][0]
        assert '/tf1/helloworld.txt.txt' == files[1][0]
        assert '/tf1/tf2/file.txt' == files[0][0]
        assert '/tf1/tf2-second/secondpage.txt' == files[2][0]
        assert '/tf1/tf2-second/thirdpage.txt' == files[3][0]
        assert files[0][1] == "2.1", (files[0][1])
        assert isinstance(files[0][2], str)

    def test_get_latest_mock_wiki_version(self):
        """Test getting the latest version of a mock wiki"""

        link = 'wiki'
        wikis = explore_wikis(
            link, os.getenv('TEST_PAT', ''), dryrun=True
            )
        assert len(wikis) == 3
        assert 'helloworld' in wikis.keys(), (
            'Missing wiki IDs'
        )
        assert 'home' in wikis.keys(), (
            'Missing wiki IDs'
        )
        assert 'anotherone' in wikis.keys(), (
            'Missing wiki IDs'
        )

        assert 'hello world' in wikis['helloworld'], (
            wikis['helloworld']
        )
        assert '~~strikethrough~~' in wikis['home'], (
            wikis['home']
        )

    def test_parse_mock_api_responses(self):
        """Using JSON stubs to simulate API responses,
        test we can parse them correctly"""

        projects, root_nodes = get_project_data(
            os.getenv('TEST_PAT', ''),
            dryrun=True
        )

        assert len(projects) == 4, (
            'Expected 4 projects in the stub data'
        )
        assert len(root_nodes) == 2, (
            'Expected 2 root nodes in the stub data'
        )
        assert root_nodes[0] == 0
        assert root_nodes[1] == 1
        assert projects[root_nodes[0]]['metadata']['id'] == 'x', (
            'Expected ID x, got: ',
            projects[root_nodes[0]]['metadata']['id']
        )
        assert projects[root_nodes[1]]['metadata']['id'] == 'y', (
            'Expected ID y, got: ',
            projects[root_nodes[1]]['metadata']['id']
        )

        assert projects[0]['metadata']['title'] == 'Test1', (
            'Expected title Test1, got: ',
            projects[0]['metadata']['title']
        )
        assert projects[0]['metadata']['id'] == 'x', (
            'Expected ID x, got: ',
            projects[0]['metadata']['id']
        )
        assert projects[1]['metadata']['title'] == 'Test2', (
            'Expected title Test2, got: ',
            projects[1]['metadata']['title']
        )
        assert projects[0]['metadata']['license'] == 'mynewlicense', (
            'Expected mynewlicense, got: ',
            projects[0]['metadata']['license']
        )
        assert projects[0]['metadata']['description'] == 'Test1 Description', (
            'Expected description Test1 Description, got: ',
            projects[0]['metadata']['description']
        )
        assert projects[1]['metadata']['description'] == 'Test2 Description', (
            'Expected description Test2 Description, got: ',
            projects[1]['description']
        )
        expected_date = '2000-01-01'
        assert str(
            projects[0]['metadata']['date_created']
        ) == expected_date, (
            f'Expected date_created {expected_date}, got: ',
            projects[0]['metadata']['date_created']
        )
        assert str(
            projects[0]['metadata']['date_modified']
        ) == expected_date, (
            f'Expected date_modified {expected_date}, got: ',
            projects[0]['metadata']['date_modified']
        )
        assert projects[0]['metadata']['tags'] == 'test1, test2, test3', (
            'Expected tags test1, test2, test3, got: ',
            projects[0]['metadata']['tags']
        )
        assert projects[1]['metadata']['tags'] == 'NA', (
            'Expected tags NA, got: ',
            projects[1]['metadata']['tags']
        )

        assert projects[0]['contributors'][0][0] == 'Test User 1', (
            "Expected contributor Test User 1, got: ",
            projects[0]['contributors'][0][0]
        )
        assert not projects[0]['contributors'][0][1], (
            "Expected contributor status False, got: ",
            projects[0]['contributors'][0][1]
        )
        link = 'https://test.osf.io/userid/'
        link_two = 'https://test.osf.io/userid2/'
        assert projects[0]['contributors'][0][2] == link, (
            f"Expected contributor link {link}, got: ",
            projects[0]['contributors'][0][2]
        )
        assert projects[0]['contributors'][1][0] == 'Test User 2', (
            "Expected contributor Test User 2, got: ",
            projects[0]['contributors'][1][0]
        )
        assert projects[0]['contributors'][1][1], (
            "Expected contributor status True, got: ",
            projects[0]['contributors'][1][1]
        )
        assert projects[0]['contributors'][1][2] == link_two, (
            f"Expected contributor link {link_two}, got: ",
            projects[0]['contributors'][1][2]
        )

        doi = projects[0]['metadata']['identifiers']
        assert doi == '10.4-2-6-25/OSF.IO/74PAD', (
            'Expected identifiers 10.4-2-6-25/OSF.IO/74PAD, got: ',
            doi
        )
        assert projects[0]['metadata']['resource_type'] == 'Other', (
            'Expected resource_type Other, got: ',
            projects[0]['metadata']['resource_type']
        )
        assert projects[0]['metadata']['resource_lang'] == 'eng', (
            'Expected resource_lang eng, got: ',
            projects[0]['metadata']['resource_lang']
        )
        assert len(projects[0]['files']) == 5
        assert '/helloworld.txt.txt' == projects[0]['files'][4][0], (
            projects[0]['files'][4][0]
        )
        assert '/tf1/helloworld.txt.txt' == projects[0]['files'][1][0], (
            projects[0]['files'][1][0]
        )
        assert '/tf1/tf2/file.txt' == projects[0]['files'][0][0], (
            projects[0]['files'][0][0]
        )
        subjects = projects[0]['metadata']['subjects']
        assert subjects == 'Education, Literature, Geography', (
            'Expected Education, Literature, Geography, got: ',
            subjects
        )
        assert len(projects[0]['wikis']) == 3
        assert projects[0]['metadata']['url'] == 'https://test.osf.io/x/', (
            'Expected URL https://test.osf.io/x/, got: ',
            projects[0]['metadata']['url']
        )
        assert projects[1]['metadata']['url'] != 'https://test.osf.io/x/', (
            'Repeated project URL'
        )

        assert projects[0]['parent'] is None, (
            'Expected no parent, got: ',
            projects[0]['parent']
        )
        assert 'a' in projects[0]['children']
        assert 'b' in projects[0]['children']

        assert projects[0]['metadata']['public']
        assert not projects[1]['metadata']['public']

        assert projects[0]['metadata']['category'] == 'Methods and Measures', (
            projects[0]['metadata']['category']
        )
        assert projects[1]['metadata']['category'] == 'Uncategorized', (
            projects[1]['metadata']['category']
        )

    def test_get_single_mock_project(self):
        projects, roots = get_project_data(
            os.getenv('TEST_PAT', ''), dryrun=True,
            project_id='x'
        )
        assert len(roots) == 1
        assert len(projects) == 3
        assert projects[0]['metadata']['id'] == 'x'
        assert projects[0]['children'] == ['a', 'b']

    def test_write_pdf_without_giving_a_folder(self):
        projects = [
            {
                'metadata': {
                    'title': 'My Project Title',
                    'id': 'id',
                    'url': 'https://test.osf.io/x',
                    'category': 'Uncategorized',
                    'description': 'This is a description of the project',
                    'date_created': datetime.datetime.fromisoformat(
                        '2025-06-12T15:54:42.105112Z'
                    ),
                    'date_modified': datetime.datetime.fromisoformat(
                        '2001-01-01T01:01:01.105112Z'
                    ),
                    'tags': 'tag1, tag2, tag3',
                    'resource_type': 'na',
                    'resource_lang': 'english',
                    'affiliated_institutions': 'University of Manchester',
                    'identifiers': 'N/A',
                    'license': 'Apache 2.0',
                    'subjects': 'sub1, sub2, sub3',
                },
                'contributors': [
                    ('Pineapple Pizza', False, 'https://test.osf.io/userid/'),
                    ('Margarita', True, 'https://test.osf.io/userid/'),
                    ('Margarine', True, 'https://test.osf.io/userid/')
                ],
                'files': [
                    ('file1.txt', None, 'https://test.osf.io/userid/'),
                    ('file2.txt', None, None),
                ],
                'funders': [],
                'wikis': {
                    'Home': 'hello world',
                    'Page2': 'another page'
                },
                "parent": None,
                'children': ['a']
            }
        ]
        root_nodes = [0]
        is_filename_match = False  # Flag for if exported PDF has expected name
        try:
            pdf_one, path_one = write_pdf(projects, root_nodes[0], '')

            title_one = projects[0]['metadata']['title'].replace(' ', '-')
            date_one = pdf_one.date_printed.strftime(
                '%Y-%m-%d %H:%M:%S %Z'
            ).replace(' ', '-')
            expected_filename = f'{title_one}-{date_one}.pdf'

            is_filename_match = expected_filename in os.listdir(os.getcwd())
        except Exception as e:
            print(e)
        finally:
            if os.path.exists(path_one):
                os.remove(path_one)

        assert is_filename_match, (
            'Unable to create file in current directory.'
        )

    def test_write_pdfs_from_mock_projects(self):
        # Put PDFs in a folder to keep things tidy
        if os.path.exists(FOLDER_OUT):
            shutil.rmtree(FOLDER_OUT)
        os.mkdir(FOLDER_OUT)

        projects = [
            {
                'metadata': {
                    'title': 'My Project Title',
                    'id': 'id',
                    'url': 'https://test.osf.io/x',
                    'category': 'Uncategorized',
                    'description': 'This is a description of the project',
                    'date_created': datetime.datetime.fromisoformat(
                        '2025-06-12T15:54:42.105112Z'
                    ),
                    'date_modified': datetime.datetime.fromisoformat(
                        '2001-01-01T01:01:01.105112Z'
                    ),
                    'tags': 'tag1, tag2, tag3',
                    'resource_type': 'na',
                    'resource_lang': 'english',
                    'affiliated_institutions': 'University of Manchester',
                    'identifiers': 'N/A',
                    'license': 'Apache 2.0',
                    'subjects': 'sub1, sub2, sub3',
                },
                'contributors': [
                    ('Pineapple Pizza', False, 'https://test.osf.io/userid/'),
                    ('Margarita', True, 'https://test.osf.io/userid/'),
                    ('Margarine', True, 'https://test.osf.io/userid/')
                ],
                'files': [
                    ('file1.txt', None, 'https://test.osf.io/userid/'),
                    ('file2.txt', None, None),
                ],
                'funders': [],
                'wikis': {
                    'Home': 'hello world',
                    'Page2': 'another page'
                },
                "parent": None,
                'children': ['a']
            },
            {
                'metadata': {
                    "title": "child1",
                    "id": "a",
                    'url': 'https://test.osf.io/a',
                },
                'contributors': [
                    (
                        'Long Double-Barrelled Name and Surname',
                        False, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name2', True, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name3', True, 'https://test.osf.io/userid/'
                    )
                ],
                'files': [
                    ('file1.txt', None, None),
                    ('file2.txt', None, None),
                ],
                'wikis': {},
                "parent": 'id',
                'children': ['b']
            },
            {
                'metadata': {
                    "title": "Second Project in new PDF",
                    "id": "c",
                    'url': 'lol',
                    'category': 'Methods and Measures'
                },
                'contributors': [
                    (
                        'Long Double-Barrelled Name and Surname',
                        False, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name2', True, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name3', True, 'https://test.osf.io/userid/'
                    )
                ],
                'files': [
                    ('file1.txt', None, None),
                    ('file2.txt', None, None),
                ],
                'wikis': {},
                "parent": None,
                'children': []
            },
            {
                'metadata': {
                    "title": "child2",
                    "id": "b",
                    'url': 'dan'
                },
                'contributors': [
                    (
                        'Long Double-Barrelled Name and Surname',
                        False, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name2', True, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name3', True, 'https://test.osf.io/userid/'
                    )
                ],
                'files': [
                    ('file1.txt', None, None),
                    ('file2.txt', None, None),
                ],
                'wikis': {},
                "parent": 'a',
                'children': []
            },
        ]

        root_nodes = [0, 2]  # Indices of root nodes in projects list

        # Get URL now as it will be removed later
        url = projects[0]['metadata']['url']
        url_comp = projects[1]['metadata']['url']

        # pdb.set_trace()
        # Can we specify where to write PDFs?
        pdf_one, path_one = write_pdf(projects, root_nodes[0], FOLDER_OUT)
        pdf_two, path_two = write_pdf(projects, root_nodes[1], FOLDER_OUT)
        files = os.listdir(FOLDER_OUT)
        assert len(files) == 2

        title_one = projects[0]['metadata']['title'].replace(' ', '-')
        title_two = projects[2]['metadata']['title'].replace(' ', '-')
        date_one = pdf_one.date_printed.strftime(
            '%Y-%m-%d %H:%M:%S %Z'
        ).replace(' ', '-')
        date_two = pdf_two.date_printed.strftime(
            '%Y-%m-%d %H:%M:%S %Z'
        ).replace(' ', '-')
        path_one_real = os.path.join(
            os.getcwd(), FOLDER_OUT,
            f'{title_one}-{date_one}.pdf'
        )
        path_two_real = os.path.join(
            os.getcwd(), FOLDER_OUT,
            f'{title_two}-{date_two}.pdf'
        )
        assert path_one == path_one_real, (
            path_one,
            path_one_real
        )
        assert path_two == path_two_real, (
            path_two,
            path_two_real
        )

        import_one = PdfReader(os.path.join(
            FOLDER_OUT, f'{title_one}-{date_one}.pdf'
        ))
        import_two = PdfReader(os.path.join(
            FOLDER_OUT, f'{title_two}-{date_two}.pdf'
        ))
        assert len(import_one.pages) == 4, (
            'Expected 4 pages in the first PDF, got: ',
            len(import_one.pages)
        )

        content_first_page = import_one.pages[0].extract_text(
            extraction_mode='layout'
        )
        content_second_page = import_two.pages[0].extract_text(
            extraction_mode='layout'
        )
        content_third_page = import_one.pages[2].extract_text(
            extraction_mode='layout'
        )
        assert f'{projects[0]['metadata']['title']}' in content_third_page, (
            content_third_page
        )
        assert f'{url}' in content_third_page, (
            content_third_page
        )
        assert f'{projects[1]['metadata']['title']}' in content_third_page
        assert f'{url_comp}' in content_third_page

        assert f'{url}' in content_first_page, (
            content_third_page
        )

        assert 'Category: Uncategorized' in content_first_page, (
            content_first_page
        )
        assert 'Category: Methods and Measures' in content_second_page, (
            content_second_page
        )

        timestamp = pdf_one.date_printed.strftime(
            '%Y-%m-%d %H:%M:%S %Z')
        assert f'Exported: {timestamp}' in content_first_page, (
            'Actual content:',
            content_first_page
        )

        # This way of string formatting compresses line lengths used
        # End of headers and table rows marked by \n\n
        contributors_table = (
            'Subjects: sub1, sub2, sub3\n\n'
            '2. Contributors\n\n'
            'Name                                               '
            'Bibliographic?            '
            'Profile Link\n\n'
            'Pineapple Pizza                                    '
            'No                        '
            'https://test.osf.io/userid/\n\n'
            'Margarita                                          '
            'Yes                       '
            'https://test.osf.io/userid/\n\n'
            'Margarine                                          '
            'Yes                       '
            'https://test.osf.io/userid/\n\n'
            '3. Files in Main Project'
        )
        assert contributors_table in content_first_page

        # This way of string formatting compresses line lengths used
        # End of headers and table rows marked by \n\n
        files_table = (
            '3. Files in Main Project\n\n'
            'OSF Storage\n\n'
            'File Name                                          '
            'Size (MB)                 '
            'Download Link\n\n'
            'file1.txt                                          '
            'N/A                       '
            'https://test.osf.io/userid/\n\n'
            'file2.txt                                          '
            'N/A                       '
            'N/A\n\n'
            '4. Wiki'
        )
        assert files_table in content_first_page

        # Remove files only if all good - keep for debugging otherwise
        os.remove(path_one)
        os.remove(path_two)

    def test_use_dryrun_in_user_default_dir(self):
        """Regression test for using --dryrun in user's default directory."""

        cwd = os.getcwd()
        try:
            # Go to user's home directory in cross-platform way
            os.chdir(os.path.expanduser("~"))
            projects, roots = get_project_data('', dryrun=True, usetest=True)
        except Exception as e:
            raise e
        finally:
            # Reverse state changes for reproducibility
            os.chdir(cwd)
            assert os.getcwd() == cwd
    
    def test_extract_project_id(self):
        """Test extracting project ID from various URL formats."""

        url = 'https://osf.io/x/'
        project_id = extract_project_id(url)
        assert project_id == 'x', f'Expected "x", got {project_id}'

        url = 'https://api.test.osf.io/v2/nodes/x/'
        project_id = extract_project_id(url)
        assert project_id == 'x', f'Expected "x", got {project_id}'

        # TODO: add test for passing a URL for test site when
        # we are using production site, and vice versa

        url = 'x'
        project_id = extract_project_id(url)
        assert project_id == 'x', f'Expected "x", got {project_id}'

        # Should just run normally
        url = ''
        project_id = extract_project_id(url)


class TestCLI(TestCase):
    @patch('osfexport.exporter.is_public', lambda x: False)
    def test_prompt_pat_if_private(self):
        pat = prompt_pat('x')
        assert pat != ''

    @patch('osfexport.exporter.is_public', lambda x: True)
    def test_prompt_pat_if_public(self):
        pat = prompt_pat('x')
        assert pat == ''

    def test_pull_projects_command_on_mocks(self):
        """Test generating a PDF from parsed project data.
        This assumes the JSON parsing works correctly."""

        if os.path.exists(FOLDER_OUT):
            shutil.rmtree(FOLDER_OUT)
        os.mkdir(FOLDER_OUT)

        runner = CliRunner()
        result = runner.invoke(
            cli, [
                'export-projects', '--dryrun',
                '--folder', FOLDER_OUT,
                '--url', ''
            ],
            input=os.getenv('TEST_PAT', ''),
            terminal_width=60
        )
        assert not result.exception, (
            result.exc_info,
            traceback.format_tb(result.exc_info[2])
        )
