import json
import os
import datetime
import urllib.request as webhelper
import io

from fpdf import FPDF, Align
from fpdf.fonts import FontFace
from mistletoe import markdown
import qrcode

API_HOST_TEST = os.getenv('API_HOST_TEST', 'https://api.test.osf.io/v2')
API_HOST_PROD = os.getenv('API_HOST_PROD', 'https://api.osf.io/v2')

STUBS_DIR = os.path.join(
    os.path.dirname(__file__), 'stubs'
)

# Global styles for PDF
BLUE = (173, 216, 230)
HEADINGS_STYLE = FontFace(emphasis="BOLD", fill_color=BLUE)

def extract_project_id(url):
    """Extract project ID from a given OSF project URL.

    Parameters
    ----------
    url: str
        URL of the OSF project.

    Returns
    -------
    str
        Project ID extracted from the URL.
    """

    project_id = url.strip("/").split("/")[-1]
    return project_id


def get_host(is_test):
    """Get API host based on flag.

    Parameters
    ----------
    is_test: bool
        If True, return test API host, otherwise return production host.

    Returns
    -------
    str
        API host URL for the test site or production site.
    """

    return API_HOST_TEST if is_test else API_HOST_PROD


def is_public(url):
    """Return boolean to indicate if a URL is public (True) or not (False).

    Parameters
    ------------
    url: str
        The URL to test.
    """

    request = webhelper.Request(url, method='GET')
    try:
        result = webhelper.urlopen(request).status
    except webhelper.HTTPError as e:
        result = e
    return result == 200


class MockAPIResponse:
    """Simulate OSF API response for testing purposes."""

    JSON_FILES = {
        'nodes': os.path.join(
            STUBS_DIR, 'nodestubs.json'),
        'x': os.path.join(
            STUBS_DIR, 'singlenode.json'),
        'affiliated_institutions': os.path.join(
            STUBS_DIR, 'institutionstubs.json'),
        'contributors': os.path.join(
            STUBS_DIR, 'contributorstubs.json'),
        'identifiers': os.path.join(
            STUBS_DIR, 'doistubs.json'),
        'custom_metadata': os.path.join(
            STUBS_DIR, 'custommetadatastub.json'),
        'root_folder': os.path.join(
            STUBS_DIR, 'files', 'rootfolders.json'),
        'root_files': os.path.join(
            STUBS_DIR, 'files', 'rootfiles.json'),
        'tf1_folder': os.path.join(
            STUBS_DIR, 'files', 'tf1folders.json'),
        'tf1-2_folder': os.path.join(
            STUBS_DIR, 'files', 'tf1folders-2.json'),
        'tf1-2_files': os.path.join(
            STUBS_DIR, 'files', 'tf2-second-folders.json'),
        'tf1_files': os.path.join(
            STUBS_DIR, 'files', 'tf1files.json'),
        'tf2_folder': os.path.join(
            STUBS_DIR, 'files', 'tf2folders.json'),
        'tf2-second_folder': os.path.join(
            STUBS_DIR, 'files', 'tf2-second-folders.json'),
        'tf2_files': os.path.join(
            STUBS_DIR, 'files', 'tf2files.json'),
        'tf2-second_files': os.path.join(
            STUBS_DIR, 'files', 'tf2-second-files.json'),
        'tf2-second-2_files': os.path.join(
            STUBS_DIR, 'files', 'tf2-second-files-2.json'),
        'license': os.path.join(
            STUBS_DIR, 'licensestub.json'),
        'subjects': os.path.join(
            STUBS_DIR, 'subjectsstub.json'),
        'wikis': os.path.join(
            STUBS_DIR, 'wikis', 'wikistubs.json'),
        'wikis2': os.path.join(
            STUBS_DIR, 'wikis', 'wikis2stubs.json'),
        'x-children': os.path.join(
            STUBS_DIR, 'components', 'x-children.json'),
        'empty-children': os.path.join(
            STUBS_DIR, 'components', 'empty-children.json'),
    }

    MARKDOWN_FILES = {
        'helloworld': os.path.join(
            STUBS_DIR, 'wikis', 'helloworld.md'),
        'home': os.path.join(
            STUBS_DIR, 'wikis', 'home.md'),
        'anotherone': os.path.join(
            STUBS_DIR, 'wikis', 'anotherone.md'),
    }

    @staticmethod
    def read(field):
        """Get mock response for a field.

        Parameters
        -----------
            field: str
                ID associated to a JSON or Markdown mock file.
                Available fields to mock are listed in class-level
                JSON_FILES and MARKDOWN_FILES attributes.

        Returns
        ------------
            Parsed JSON dictionary or Markdown."""

        if field in MockAPIResponse.JSON_FILES.keys():
            with open(MockAPIResponse.JSON_FILES[field], 'r') as file:
                return json.load(file)
        elif field in MockAPIResponse.MARKDOWN_FILES.keys():
            with open(MockAPIResponse.MARKDOWN_FILES[field], 'r') as file:
                return file.read()
        else:
            return {}


class PDF(FPDF):
    """Custom PDF class to implement extra customisation.
    Attributes:
        date_printed: datetime
            Date and time when the project was exported.
        url: str
            Current URL to include in QR codes.
        parent_url: str
            URL of root project to use in component sections.
        parent_title: str
            Title of root project to use in component sections.
    """

    def __init__(self, url='', parent_url='', parent_title=''):
        super().__init__()
        self.date_printed = datetime.datetime.now().astimezone()
        self.parent_url = parent_url
        self.parent_title = parent_title
        self.url = url

    def generate_qr_code(self):
        qr = qrcode.make(self.url)
        img_byte_arr = io.BytesIO()
        qr.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr

    def footer(self):
        self.set_y(-15)
        self.set_x(-30)
        self.set_font('Times', size=10)
        self.cell(0, 10, f"Page: {self.page_no()}", align="C")
        self.set_x(10)
        timestamp = self.date_printed.strftime(
            '%Y-%m-%d %H:%M:%S %Z'
        )
        self.cell(0, 10, f"Exported: {timestamp}", align="L")
        self.set_x(10)
        self.set_y(-25)
        qr_img = self.generate_qr_code()
        self.image(qr_img, w=15, h=15, x=Align.C)


# Reduce response size by applying filters on fields
URL_FILTERS = {
    'identifiers': {
        'category': 'doi'
    }
}


def call_api(url, pat, method='GET', per_page=100, filters={}, is_json=True):
    """Call OSF v2 API methods.

    Parameters
    ----------
    url: str
        URL to API method/resource/query.
    method: str
        HTTP method for the request.
    pat: str
        Personal Access Token to authorise a user with.
    per_page: int
        Number of items to include in a JSON page for API responses.
        The maximum is 100.
    filters: dict
        Dictionary of query parameters to filter results with.

        Example Input: {'category': 'project', 'title': 'ttt'}
        Example Query String: ?filter[category]=project&filter[title]=ttt
    is_json: bool
        If true, set API version to get correct API responses.

    Returns
    ----------
        result: HTTPResponse
            Response to the request from the API.
    """
    if (filters or per_page) and method == 'GET':
        query_string = '&'.join([f'filter[{key}]={value}'
                                 for key, value in filters.items()
                                 if not isinstance(value, dict)])
        if per_page:
            query_string += f'&page[size]={per_page}'
        url = f'{url}?{query_string}'

    request = webhelper.Request(url, method=method)
    request.add_header('Authorization', f'Bearer {pat}')

    # Pin API version so that JSON has correct format
    API_VERSION = '2.20'
    if is_json:
        request.add_header(
            'Accept',
            f'application/vnd.api+json;version={API_VERSION}'
        )
    result = webhelper.urlopen(request)
    return result


def explore_file_tree(curr_link, pat, dryrun=True):
    """Explore and get names of files stored in OSF.

    Parameters
    ----------
    curr_link: string
        URL/name to use to get real/mock files and folders.
    pat: string
        Personal Access Token to authorise a user.
    dryrun: bool
        Flag to indicate whether to use mock JSON files or real API calls.

    Returns
    ----------
        files_found: list[str]
            List of file paths found in the project."""

    FILE_FILTER = {
        'kind': 'file'
    }
    FOLDER_FILTER = {
        'kind': 'folder'
    }
    per_page = 100

    files_found = []

    is_last_page_folders = False
    while not is_last_page_folders:
        if dryrun:
            folders = MockAPIResponse.read(f"{curr_link}_folder")
        else:
            folders = json.loads(
                call_api(
                    curr_link, pat,
                    per_page=per_page, filters=FOLDER_FILTER
                ).read()
            )

        # Find deepest subfolders first to avoid missing files
        try:
            for folder in folders['data']:
                links = folder['relationships']['files']['links']
                link = links['related']['href']
                files_found += explore_file_tree(link, pat, dryrun=dryrun)
        except KeyError:
            pass

        # For each folder, loop through pages for its files
        is_last_page_files = False
        while not is_last_page_files:
            if dryrun:
                files = MockAPIResponse.read(f"{curr_link}_files")
            else:
                files = json.loads(
                    call_api(
                        curr_link, pat,
                        per_page=per_page, filters=FILE_FILTER
                    ).read()
                )
            try:
                for file in files['data']:
                    size = file['attributes']['size']
                    size_mb = size / (1024 ** 2)  # Convert bytes to MB
                    data = (
                        file['attributes']['materialized_path'],
                        str(round(size_mb, 2)),
                        file['links']['download']
                    )
                    files_found.append(data)
            except KeyError:
                pass
            curr_link = files['links']['next']
            if curr_link is None:
                is_last_page_files = True

        curr_link = folders['links']['next']
        if curr_link is None:
            is_last_page_folders = True

    return files_found


def explore_wikis(link, pat, dryrun=True):
    """Get wiki contents for a particular project.

    Parameters:
    -------------
    link: str
        URL to project wikis or name of wikis field to access mock JSON.
    pat: str
        Personal Access Token to authenticate a user with.
    dryrun: bool
        Flag to indicate whether to use mock JSON files or real API calls.

    Returns
    ---------------
    wikis: List of JSON representing wikis for a project."""

    wiki_content = {}
    is_last_page = False
    if dryrun:
        wikis = MockAPIResponse.read('wikis')
    else:
        wikis = json.loads(
            call_api(link, pat).read()
        )

    while not is_last_page:
        for wiki in wikis['data']:
            if dryrun:
                content = MockAPIResponse.read(wiki['attributes']['name'])
            else:
                # Decode Markdown content to allow parsing later on
                content = call_api(
                    wiki['links']['download'], pat=pat, is_json=False
                ).read().decode('utf-8')
            wiki_content[wiki['attributes']['name']] = content

        # Go to next page of wikis if pagination applied
        # so that we don't miss wikis
        link = wikis['links']['next']
        if not link:
            is_last_page = True
        else:
            if dryrun:
                wikis = MockAPIResponse.read(link)
            else:
                wikis = json.loads(
                    call_api(link, pat).read()
                )

    return wiki_content


def get_project_data(pat, dryrun=False, project_id='', usetest=False):
    """Pull and list projects for a user from the OSF.

    Parameters
    ----------
    pat: str
        Personal Access Token to authorise a user with.
    dryrun: bool
        If True, use test data from JSON stubs to mock API calls.
    project_id: str
        Optional ID for a specific OSF project to export.
    usetest: bool
        If True, use test API host, otherwise use production host.

    Returns
    ----------
        projects: list[dict]
            List of dictionaries representing projects.
    """

    api_host = get_host(usetest)

    # Reduce query size by getting root nodes only
    node_filter = {
        'parent': '',
    }

    if not dryrun:
        if project_id:
            result = call_api(
                f'{api_host}/nodes/{project_id}/', pat
            )
            # Put data into same format as if multiple nodes found
            nodes = {'data': [json.loads(result.read())['data']]}
        else:
            result = call_api(
                f'{api_host}/users/me/nodes/', pat,
                filters=node_filter
            )
            nodes = json.loads(result.read())
    else:
        if project_id:
            # Put data into same format as if multiple nodes found
            nodes = {'data': [MockAPIResponse.read(project_id)['data']]}
        else:
            nodes = MockAPIResponse.read('nodes')

    projects = []
    root_nodes = []  # Track indexes of root nodes for quick access
    added_node_ids = set()  # Track added node IDs to avoid duplicates

    for idx, project in enumerate(nodes['data']):
        if project['id'] in added_node_ids:
            continue
        else:
            added_node_ids.add(project['id'])

        # Define nice representations of categories if needed
        CATEGORY_STRS = {
            '': 'Uncategorized',
            'methods and measures': 'Methods and Measures'
        }

        project_data = {
            'metadata': {
                'title': project['attributes']['title'],
                'id': project['id'],
                'url': project['links']['html'],
                'description': project['attributes']['description'],
                'category': CATEGORY_STRS[project['attributes']['category']]
                    if project['attributes']['category'] in CATEGORY_STRS
                    else project['attributes']['category'].title(),
                'date_created': datetime.datetime.fromisoformat(
                    project['attributes']['date_created']
                ).astimezone().strftime('%Y-%m-%d'),
                'date_modified': datetime.datetime.fromisoformat(
                    project['attributes']['date_modified']
                ).astimezone().strftime('%Y-%m-%d'),
                'tags': ', '.join(project['attributes']['tags'])
                    if project['attributes']['tags'] else 'NA',
                'public': project['attributes']['public'],
                'resource_type': 'NA',
                'resource_lang': 'NA',
                'funders': []
            },
            'files': [],
            'wikis': {}
        }

        # Resource type/lang/funding info share specific endpoint
        # that isn't linked to in user nodes' responses
        if dryrun:
            metadata = MockAPIResponse.read('custom_metadata')
        else:
            metadata = json.loads(call_api(
                f"{api_host}/custom_item_metadata_records/{project['id']}/",
                pat
            ).read())
        metadata = metadata['data']['attributes']
        resource_type = metadata['resource_type_general']
        resource_lang = metadata['language']
        project_data['metadata']['resource_type'] = resource_type
        project_data['metadata']['resource_lang'] = resource_lang
        for funder in metadata['funders']:
            project_data['metadata']['funders'].append(funder)

        relations = project['relationships']

        # Get list of files in project
        if dryrun:
            link = 'root'
            use_mocks = True
        else:
            link = relations['files']['links']['related']['href']
            link += 'osfstorage/'  # ID for OSF Storage
            use_mocks = False
        project_data['files'] = explore_file_tree(link, pat, dryrun=use_mocks)

        # These attributes need link traversal to get their data
        # Most should be part of the project metadata
        METADATA_RELATIONS = [
            'affiliated_institutions',
            'identifiers',
            'license',
            'subjects',
        ]
        RELATION_KEYS = METADATA_RELATIONS + ['contributors']
        for key in RELATION_KEYS:
            if not dryrun:
                # Check relationship exists and can get link to linked data
                # Otherwise just pass a placeholder dict
                try:
                    link = relations[key]['links']['related']['href']
                    json_data = json.loads(
                        call_api(
                            link, pat,
                            filters=URL_FILTERS.get(key, {})
                        ).read()
                    )
                except KeyError:
                    if key == 'subjects':
                        raise KeyError()  # Subjects should have a href link
                    json_data = {'data': None}
            else:
                json_data = MockAPIResponse.read(key)

            values = []
            if isinstance(json_data['data'], list):
                for item in json_data['data']:
                    # Required data can either be embedded or in attributes
                    if 'embeds' in item and key != "subjects":
                        if 'users' in item['embeds']:
                            values.append((
                                item['embeds']['users']['data']
                                ['attributes']['full_name'],
                                item['attributes']['bibliographic'],
                                item['embeds']['users']['data']
                                ['links']['html']
                            ))
                        else:
                            values.append(item['embeds']['attributes']['name'])
                    else:
                        if key == 'identifiers':
                            values.append(item['attributes']['value'])
                        elif key == 'subjects':
                            values.append(item['attributes']['text'])
                        else:
                            values.append(item['attributes']['name'])

            if isinstance(json_data['data'], dict):  # e.g. license field
                values.append(json_data['data']['attributes']['name'])

            if isinstance(values, list):
                if key != 'contributors':
                    values = ', '.join(values)

            if key in METADATA_RELATIONS:
                project_data['metadata'][key] = values
            else:
                project_data[key] = values

        project_data['wikis'] = explore_wikis(
            f'{api_host}/nodes/{project['id']}/wikis/',
            pat=pat, dryrun=dryrun
        )

        if 'links' in project['relationships']['parent']:
            project_data['parent'] = project['relationships']['parent'][
                'links']['related']['href'].split('/')[-1]
        else:
            project_data['parent'] = None
            root_nodes.append(idx)
        children_link = relations['children']['links']['related']['href']
        if dryrun:
            children = MockAPIResponse.read(children_link)
        else:
            children = json.loads(
                call_api(children_link, pat).read()
            )
        project_data['children'] = []
        for child in children['data']:
            project_data['children'].append(child['id'])
            nodes['data'].append(child)

        projects.append(project_data)

    return projects, root_nodes


def write_pdf(projects, root_idx, folder=''):
    """Make PDF for each project.

    Parameters
    ------------
        projects: dict[str, str|tuple]
            Projects found to export into the PDF.
        root_idx: int
            Position of root node (no parent) in the projects list.
            This is used for accessing root projects without sorting the list.
        folder: str
            The path to the folder to output the project PDFs in.
            Default is the current working directory.

    Returns
    ------------
        pdfs: list
            List of created PDF files.
    """

    def write_list_section(key, fielddict, pdf):
        """Handle writing fields based on their type to PDF.
        Possible types are lists or strings.

        Parameters
        -----------
            key: str
                Name of the field to write.
            fielddict: dict
                Dictionary containing the field data.
            pdf: PDF
                PDF object to write to."""

        # Set nicer display names for certain PDF fields
        pdf_display_names = {
            'identifiers': 'DOI',
            'funders': 'Support/Funding Information'
        }
        if key in pdf_display_names:
            field_name = pdf_display_names[key]
        else:
            field_name = key.replace('_', ' ').title()
        if isinstance(fielddict[key], list):
            pdf.write(0, '\n')
            pdf.set_font('Times', size=14)
            pdf.multi_cell(
                0, h=0,
                text=f'**{field_name}**\n\n',
                align='L', markdown=True
            )
            pdf.set_font('Times', size=12)
            for item in fielddict[key]:
                for subkey in item.keys():
                    if subkey in pdf_display_names:
                        field_name = pdf_display_names[subkey]
                    else:
                        field_name = subkey.replace('_', ' ').title()

                    pdf.multi_cell(
                        0, h=0,
                        text=f'**{field_name}:** {item[subkey]}\n\n',
                        align='L', markdown=True
                    )
                pdf.write(0, '\n')
        else:
            pdf.multi_cell(
                0,
                h=0,
                text=f'**{field_name}:** {fielddict[key]}\n\n',
                align='L',
                markdown=True
            )

    def write_project_body(pdf, project):
        """Write the body of a project to the PDF.

        Parameters
        -----------
            pdf: PDF
                PDF object to write to.
            project: dict
                Dictionary containing project data to write.
            parent_title: str
                Title of the parent project.
        Returns
        -----------
            pdf: PDF"""
        pdf.add_page()
        pdf.set_line_width(0.05)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        pdf.set_font('Times', size=12)
        wikis = project['wikis']

        # Write header section
        pdf.set_font('Times', size=18, style='B')
        # Write parent header and title first
        if pdf.parent_title:
            pdf.multi_cell(0, h=0, text=f'{pdf.parent_title}\n', align='L')
        if pdf.parent_url:
            pdf.set_font('Times', size=12)
            pdf.cell(
                text='Main Project URL:', align='L'
            )
            pdf.cell(
                text=f'{pdf.parent_url}\n', align='L', link=pdf.parent_url
            )
            pdf.write(0, '\n\n')

        # Check if title, url is of parent's to avoid duplication
        title = project['metadata']['title']
        if pdf.parent_title != title:
            pdf.set_font('Times', size=18, style='B')
            pdf.multi_cell(0, h=0, text=f'{title}\n', align='L')

        # Pop URL field to avoid printing it out in Metadata section
        url = project['metadata'].pop('url', '')

        pdf.url = url  # Set current URL to use in QR codes
        qr_img = pdf.generate_qr_code()
        pdf.image(qr_img, w=30, x=Align.R, y=5)

        pdf.set_font('Times', size=12)
        if url and pdf.parent_url != url:
            pdf.cell(
                text='Component URL:',
                align='L'
            )
            pdf.cell(
                text=f'{url}',
                align='L',
                link=url
            )
            pdf.write(0, '\n\n')

        pdf.ln()
        pdf.ln()

        # Write title for metadata section, then actual fields
        pdf.set_font('Times', size=16, style='B')
        pdf.multi_cell(0, h=0, text='1. Project Metadata\n', align='L')
        pdf.set_font('Times', size=12)
        for key in project['metadata']:
            write_list_section(key, project['metadata'], pdf)
        pdf.write(0, '\n')
        pdf.write(0, '\n')

        # Write Contributors in table
        pdf.set_font('Times', size=16, style='B')
        pdf.multi_cell(0, h=0, text='2. Contributors\n', align='L')
        pdf.set_font('Times', size=12)
        with pdf.table(
            headings_style=HEADINGS_STYLE,
            col_widths=(1, 0.5, 1)
        ) as table:
            row = table.row()
            row.cell('Name')
            row.cell('Bibliographic?')
            row.cell('Profile Link')
            for data_row in project['contributors']:
                row = table.row()
                for idx, datum in enumerate(data_row):
                    if datum is True:
                        datum = 'Yes'
                    if datum is False:
                        datum = 'No'
                    if idx == 2:
                        row.cell(text=datum, link=datum)
                    else:
                        row.cell(datum)
        pdf.write(0, '\n')
        pdf.write(0, '\n')

        # List files stored in storage providers
        # For now only OSF Storage is involved
        pdf.set_font('Times', size=16, style='B')
        pdf.multi_cell(0, h=0, text='3. Files in Main Project\n', align='L')
        pdf.write(0, '\n')
        pdf.set_font('Times', size=14, style='B')
        pdf.multi_cell(0, h=0, text='OSF Storage\n', align='L')
        pdf.set_font('Times', size=12)
        if len(project['files']) > 0:
            with pdf.table(
                headings_style=HEADINGS_STYLE,
                col_widths=(1, 0.5, 1)
            ) as table:
                row = table.row()
                row.cell('File Name')
                row.cell('Size (MB)')
                row.cell('Download Link')
                for data_row in project['files']:
                    row = table.row()
                    for idx, datum in enumerate(data_row):
                        if datum is True:
                            datum = 'Yes'
                        if datum is False or datum is None:
                            datum = 'N/A'
                        if idx == 2:
                            row.cell(text=datum, link=datum)
                        else:
                            row.cell(datum)
        else:
            pdf.write(0, '\n')
            pdf.multi_cell(
                0, h=0, text='No files found for this project.\n', align='L'
            )
            pdf.write(0, '\n')

        # Write wikis separately to more easily handle Markdown parsing
        pdf.ln()
        pdf.set_font('Times', size=18, style='B')
        pdf.multi_cell(0, h=0, text='4. Wiki\n', align='L')
        pdf.ln()
        for i, wiki in enumerate(wikis.keys()):
            pdf.set_font('Times', size=16, style='B')
            pdf.multi_cell(0, h=0, text=f'{wiki}\n')
            pdf.set_font('Times', size=12)
            html = markdown(wikis[wiki])
            pdf.write_html(html)
            if i < len(wikis.keys())-1:
                pdf.add_page()

        return pdf

    def explore_project_tree(project, projects, pdf=None):
        """Recursively find child projects and write them to the PDF.

        Parameters
        -----------
            project: dict
                Dictionary containing project data to write.
            projects: list[dict]
                List of all projects to explore.
            pdf: PDF
                PDF object to write to. If None, a new PDF will be created.
            parent_title: str
                Title of the parent project.

        Returns
        -----------
            pdf: PDF
                PDF object with the project and its children written to it."""

        # Start with no PDF at root projects
        if not pdf:
            pdf = PDF(
                parent_title=project['metadata']['title'],
                parent_url=project['metadata']['url']
            )

        # Add current project to PDF
        pdf = write_project_body(pdf, project)

        # Do children last so that come at end of the PDF
        children = project['children']
        for child_id in children:
            child_project = next(
                (p for p in projects if p['metadata']['id'] == child_id), None
            )
            if child_project:
                pdf = explore_project_tree(
                    child_project, projects, pdf=pdf
                )

        return pdf

    curr_project = projects[root_idx]
    title = curr_project['metadata']['title']
    pdf = explore_project_tree(curr_project, projects)

    # Remove spaces in file name for better behaviour on Linux
    # Add timestamp to allow distinguishing between PDFs at a glance
    timestamp = pdf.date_printed.strftime(
        '%Y-%m-%d %H:%M:%S %Z'
    ).replace(' ', '-')
    filename = f'{title.replace(' ', '-')}-{timestamp}.pdf'

    if folder:
        if not os.path.exists(folder):
            os.mkdir(folder)
        path = os.path.join(os.getcwd(), folder, filename)
    else:
        path = os.path.join(os.getcwd(), filename)
    pdf.output(path)

    return pdf, path
