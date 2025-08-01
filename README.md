# OSF Project Exporter

This is a CLI tool for exporting research project data and files from the [OSF website](https://osf.io/). This is to prototype tool to export projects from the OSF website to a PDF, allowing users to back up, share or document their OSF projects in an offline medium.

## Development Setup

### Docker

You can setup a Docker container with this tool installed as a Python package:

1. [Install and setup Docker and Docker Desktop on your local machine](https://docs.docker.com/desktop/).
2. Clone this repository onto your local machine.
3. On the OSF website, create or log in to your account.  Set up a personal access token (PAT) by going into your account settings, selecting "Personal access tokens" in the left side menu, and clicking "Create token". You should give the token a name that helps you remember why you made it, like "PDF export", and choose the "osf.full_read" scope - this allows this token to read all public and private projects on your account. You can delete this token once you have finished exporting your projects.
4. Create a `.env` file and add your personal access token to it (see `.env.template`.)
5. In the root of this repository, run `docker compose up --build -d` to setup a container.
6. Use `docker compose exec -it cli <commands>` to run CLI tool commands (e.g. `export-projects`) or run unit tests (i.e. `python -m unittest`.)

### Virtual Environment

You could also setup a Python virtual environment (e.g. using virtualenv):

1. Clone this repository onto your local machine.
2. Create a virtual environment, e.g., ``virtualenv myenv --python='"/usr/bin/python3.12"'``. Make sure your virtual environment is setup to use Python 3.12 or above.
3. Activate your virtual environment and run ``pip install -e osfio-export-tool` to install the CLI tool inside the environment.
4. From TestPyPI: `python3 -m pip install --index-url https://test.pypi.org/simple/ --no-deps osfio-export-tool==0.0.5`, and install other requirements separately via `pip install -r requirements.txt`.
5. On the OSF website, create or log in to your account.  Set up a personal access token (PAT) by going into your account settings, selecting "Personal access tokens" in the left side menu, and clicking "Create token". You should give the token a name that helps you remember why you made it, like "PDF export", and choose the "osf.full_read" scope - this allows this token to read all public and private projects on your account. You can delete this token once you have finished exporting your projects.

## Usage

- Run `clirun` to get a list of basic commands you can use.
- To see what a command needs as input, type `--help` after the command name (e.g. `clirun show-welcome --help`; `clirun --help`)
- To export all your projects from the OSF into a PDF, run `clirun export-projects`.
