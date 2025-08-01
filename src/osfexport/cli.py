import os
import urllib.request as webhelper

import click

import osfexport.exporter as exporter

API_HOST_TEST = os.getenv('API_HOST_TEST', 'https://api.test.osf.io/v2')
API_HOST_PROD = os.getenv('API_HOST_PROD', 'https://api.osf.io/v2')


def prompt_pat(project_id='', usetest=False):
    """
    Ask for a PAT if exporting a single project or all projects a user has.

    Parameters
    -------------
        project_id: str
            ID of a single project to export.
            If one provided then ask for a PAT.
        usetest: bool
            Flag to indicate whether to use the test/production API server.

    Returns
    -----------------
        pat: str
            Personal Access Token to use to authorise a user.
    """

    if usetest:
        api_host = API_HOST_TEST
    else:
        api_host = API_HOST_PROD

    if not project_id:
        pat = click.prompt(
            'Please enter your PAT to export all your projects',
            type=str,
            hide_input=True
        )
    elif not exporter.is_public(f'{api_host}/nodes/{project_id}/'):
        pat = click.prompt(
            'Please enter your PAT to export this private project',
            type=str,
            hide_input=True
        )
    else:
        pat = ''

    return pat


@click.command()
@click.option('--pat', type=str, default='',
              prompt='Enter your PAT', prompt_required=False, hide_input=True,
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
def export_projects(folder, pat='', dryrun=False, url='', usetest=False):
    """Pull and export OSF projects to a PDF file.
    You can export all projects you have access to, or one specific one
    with the --url option."""

    project_id = ''
    if url:
        project_id = exporter.extract_project_id(url)
        click.echo(f'Extracting project with ID: {project_id}')
    else:
        click.echo('No project ID provided, extracting all projects.')

    if not pat:
        pat = prompt_pat(project_id=project_id, usetest=usetest)

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
