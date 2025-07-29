import os
import urllib.request as webhelper

import click

import exporter as exporter

API_HOST_TEST = os.getenv('API_HOST_TEST', 'https://api.test.osf.io/v2')
API_HOST_PROD = os.getenv('API_HOST_PROD', 'https://api.osf.io/v2')


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


@click.command()
@click.option('--pat', type=str, default='',
              prompt=True, hide_input=True,
              help='Personal Access Token to authorise OSF account access.')
@click.option('--dryrun', is_flag=True, default=False,
              help='If enabled, use mock responses in place of the API.')
@click.option('--usetest', is_flag=True, default=False,
              help=f"""If passed, set {API_HOST_TEST} as the API hostname.
              Otherwise, {API_HOST_PROD} is the default hostname.""")
@click.option('--folder', type=str, default='',
              help='The folder path to export PDFs to.')
@click.option('--url', type=str, default='',
              help="""A link to one project you want to export.
              The project ID should be at the end.

              For example: https://osf.io/dry9j/

              Leave blank to export all projects you have access to.""")
def export_projects(pat, folder, dryrun=False, url='', usetest=False):
    """Pull and export OSF projects to a PDF file.
    You can export all projects you have access to, or one specific one
    with the --url option."""

    project_id = ''
    if url:
        project_id = extract_project_id(url)
        click.echo(f'Extracting project with ID: {project_id}')
    else:
        click.echo('No project ID provided, extracting all projects.')

    click.echo('Downloading project data...')
    projects, root_nodes = exporter.get_project_data(
        pat, dryrun=dryrun, project_id=project_id, usetest=usetest
    )
    click.echo(f'Found {len(root_nodes)} projects.')

    for idx in root_nodes:
        title = projects[idx]['metadata']['title']
        click.echo(f'Exporting project {title}...')
        pdf, path = exporter.write_pdf(projects, idx, folder)
        click.echo(f'Project exported to {path}')


@click.command()
@click.option('--pat', type=str, default='',
              prompt=True, hide_input=True,
              help='Personal Access Token to authorise OSF account access.')
@click.option('--usetest', is_flag=True, default=False,
              help="""Use this to connect to the test API environment.
              Otherwise, the production environment will be used.""")
def show_welcome(pat, usetest):
    """Get a welcome message from the OSF site.
    This is for testing if we can connect to the API."""

    if usetest:
        api_host = API_HOST_TEST
    else:
        api_host = API_HOST_PROD

    request = webhelper.Request(f'{api_host}/', method='GET')
    request.add_header('Authorization', f'Bearer {pat}')
    result = webhelper.urlopen(request)
    click.echo(result.read())
    click.echo(result.status)


# Group will be used as entry point for CLI
@click.group()
def cli():
    pass


cli.add_command(export_projects)
cli.add_command(show_welcome)
