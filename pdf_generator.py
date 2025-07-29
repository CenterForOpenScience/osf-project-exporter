'''
## =================================================================================================
## Title: Python script to create OSF Project to PDF                                              ##
## Project:                                                                                       ##
##      Export OSF Project to PDF - Centre for Open Science (CoS) & University of Manchester (UoM)##
## UoM Team:                                                                                      ##
##      Ramiro Bravo, Sarah Jaffa, Benito Matischen                                               ##
## Author(s):                                                                                     ##
##       Ramiro Bravo - ramiro.bravo@manchester.ac.uk - ramirobravo@gmail.com                     ##
## Create date:                                                                                   ##
##       July-2025                                                                                ##
## Description:                                                                                   ##
##      The script generates the a PDF file for a specific OSF.io project using OSF API.          ##
## Parameters:                                                                                    ##
##      project_id:     For exapmle: "kzc68" from the URL https://osf.io/kzc68/                   ##
##      isTest:         To define using the API in Production or Test                             ##
##      output_name:    Temporaty not in use.                                                     ##
##      api_token:      Receives the API Key provided by the user or empty for public projects.   ##
##      project_type:   Public or Private OSF project.                                            ##  
##                                                                                                ##
## =================================================================================================
'''


import os
import io
import requests
#import qrcode
#import dotenv
from PIL import Image
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak,
    Image as RLImage, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
#from google.colab import drive
from datetime import datetime
from pytz import timezone # Import timezone from pytz


# Mount Google Drive and load environment variables
#drive.mount('/content/drive')
import dotenv
dotenv.load_dotenv(dotenv_path=".env")

OSF_TOKEN = os.getenv("OSF_TOKEN", "")

BASE_URL = "https://api.osf.io/v2/nodes/"

#HEADERS = {"Authorization": f"Bearer {OSF_TOKEN}"} if OSF_TOKEN else {}
#HEADERS = {"Authorization": f"Bearer {OSF_TOKEN}"} if OSF_TOKEN else {}
HEADERS = None

timestamp = datetime.now(timezone("UTC")).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
project_qrcode = None

def get_headers(project_type):
    if project_type == "Private":
        _headers= HEADERS = {"Authorization": f"Bearer {OSF_TOKEN}"}
    else:
        _headers = HEADERS = {"Authorization": {}}
    return _headers


def fetch_project_metadata(project_id):
    r = requests.get(f"{BASE_URL}{project_id}/?embed=affiliated_institutions", headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]

def fetch_contributors(project_id):
    r = requests.get(f"{BASE_URL}{project_id}/contributors/?embed=users", headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]

def fetch_components(project_id):
    r = requests.get(f"{BASE_URL}{project_id}/children/", headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]


def fetch_files(component_id, storage_provider="osfstorage"):
    files_api = f"{BASE_URL}{component_id}/files/{storage_provider}/"
    all_files = []

    def traverse_files(api_url, path_prefix=""):
        response = requests.get(api_url, headers=HEADERS)
        response.raise_for_status()
        entries = response.json().get("data", [])

        for entry in entries:
            kind = entry["attributes"]["kind"]
            name = entry["attributes"]["name"]
            #path_prefix = ""
            full_path = f"{path_prefix}/{name}" if path_prefix else name

            if kind == "file":
                size_bytes = entry["attributes"]["size"] or 0
                #size_gb = size_bytes / (1024 ** 3)  # Convert bytes to GB
                size_mb = size_bytes / (1024 ** 2)  # Convert bytes to MB
                all_files.append({
                    "name": f"/{full_path}",  # force root-style path
                    "size": round(size_mb, 2),
                    "link": entry["links"]["download"]
                })
            elif kind == "folder":
                next_url = entry["relationships"]["files"]["links"]["related"]["href"]
                traverse_files(next_url, full_path)

    traverse_files(files_api)
    return all_files


def fetch_wiki_pages(project_id):
    r = requests.get(f"{BASE_URL}{project_id}/wikis/", headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]

def fetch_wiki_content_by_id(page_id):
    try:
        r = requests.get(f"https://api.osf.io/v2/wikis/{page_id}/content/", headers=HEADERS)
        r.raise_for_status()
        #return r.json()["data"]["attributes"]["content"]
        return r.text
    except Exception:
        return None

def generate_qr_code(url):
    import qrcode
    qr = qrcode.make(url)
    img_byte_arr = io.BytesIO()
    qr.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

def render_metadata_section(metadata, story, styles, timestamp):
    story.append(Paragraph("1. Project Metadata", styles["MyHeading2"]))
    meta_fields = [
        ("Title", metadata["attributes"].get("title", "N/A")),
        ("Description", metadata["attributes"].get("description", "No description provided")),
        ("Date Created", metadata["attributes"].get("date_created", "N/A")[:10]),
        ("Last Modified", metadata["attributes"].get("date_modified", "N/A")[:10]),
        ("Category", metadata["attributes"].get("category", "N/A")),
        ("Public?", "Yes" if metadata["attributes"].get("public", False) else "No"),
        ("Registration?", "Yes" if metadata["attributes"].get("registered", False) else "No"),
        ("Tags", metadata["attributes"].get("tags", "N/A")),
        ("Current Permissions", metadata["attributes"].get("current_user_permissions", "N/A")),
        ("DOI", metadata["attributes"].get("doi", "N/A")),
        ("Exported At", timestamp)
    ]
    for label, value in meta_fields:
        story.append(Paragraph(f"<b>{label}:</b> {value}", styles["Normal"]))

    institutions = metadata.get("embeds", {}).get("affiliated_institutions", {}).get("data", [])
    names = ", ".join([i["attributes"]["name"] for i in institutions]) if institutions else "None listed"
    story.append(Paragraph(f"<b>Affiliated Institution(s):</b> {names}", styles["Normal"]))
    story.append(Spacer(1, 12))

def render_contributors_section(contributors, story, styles):
    story.append(Paragraph("2. Contributors", styles["MyHeading2"]))
    if not contributors:
        story.append(Paragraph("No contributors found.", styles["Normal"]))
        return

    data = [["Name", "Bibliographic?", "Email (if available)"]]
    for c in contributors:
        name = c["embeds"]["users"]["data"]["attributes"]["full_name"]
        biblio = "Yes" if c["attributes"].get("bibliographic", False) else "No"
        email = c["embeds"]["users"]["data"]["attributes"].get("email", "N/A")
        data.append([name, biblio, email])

    table = Table(data, colWidths=[2.5*inch, 1*inch, 2.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))

def render_file_table(files, story, styles, heading=None):
    if heading:
        story.append(Paragraph(heading, styles["MyHeading2"]))
    if not files:
        story.append(Paragraph("3. No files available.", styles["Normal"]))
        return
    story.append(Paragraph("3. Files OSF Storage", styles["MyHeading2"]))
    if not files:
        story.append(Paragraph("3. No files available.", styles["Normal"]))
        return
    table_data = [["File Name", "Size \n(MB)", "Download Link"]]
    for f in files:
        table_data.append([f["name"], f["size"] if f["size"] else "N/A", f["link"]])
    table = Table(table_data, colWidths=[4*inch, 0.5*inch, 2.8*inch])
    '''
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    '''
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),  # Header font size

        # Data row styling
        ('FONTSIZE', (0, 1), (-1, -1), 8),  # Data font size
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),

        # Grid for all
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))

def render_wiki_section(project_id, story, styles):
    story.append(Paragraph("4. Wiki", styles["MyHeading2"]))
    try:
        wiki_pages = fetch_wiki_pages(project_id)
        if not wiki_pages:
            story.append(Paragraph("No wiki pages found.", styles["Normal"]))
            return
        for page in wiki_pages:
            title = page["attributes"].get("name", "Untitled")
            page_id = page["id"]
            #added for debug
            story.append(Paragraph(page_id.replace('\n','<br/>'), styles["Normal"]))
            #end added
            content = fetch_wiki_content_by_id(page_id)
            story.append(Paragraph(title, styles["MyHeading3"]))
            if content:
                story.append(Paragraph(content.replace('\n', '<br/>'), styles["Normal"]))
            else:
                story.append(Paragraph("No content returned or unauthorized access", styles["Normal"]))
            story.append(Spacer(1, 12))
    except Exception as e:
        story.append(Paragraph("Error", styles["MyHeading3"]))
        story.append(Paragraph(f"Could not fetch wiki: {e}", styles["Normal"]))

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from functools import partial
from datetime import datetime
import os

def add_page_number(canvas, doc, timestamp, project_qrcode):
    canvas.saveState()
    canvas.setFont('Times-Roman', 10)
    page_number_text = f"{doc.page}"

    canvas.drawString(0.75 * inch, 0.75 * inch, f"Exported: {timestamp}")
    canvas.drawString(7.25 * inch, 0.75 * inch, f"Page: {page_number_text}")

    # Draw QR Code on each page
    if project_qrcode:
        canvas.drawImage(project_qrcode, 4.00 * inch, 0.75 * inch, width=0.5 * inch, height=0.5 * inch)

    canvas.restoreState()

def build_pdf(project_id, isTest=False, output_path=None, api_token=None, project_type=None):
    token = api_token
    HEADERS = get_headers(project_type)

    if project_type == "Private":
        token = api_token
        if not token:
            from dotenv import load_dotenv
            load_dotenv()
            token = os.getenv("OSF_TOKEN")
        if not token:
            raise ValueError("No OSF token provided.")

    metadata = fetch_project_metadata(project_id)
    contributors = fetch_contributors(project_id)
    components = fetch_components(project_id)

    project_url = f"https://{'test' if isTest else 'osf'}.io/{project_id}/"
    #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp = datetime.now(timezone("UTC")).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

    doc = SimpleDocTemplate(output_path, pagesize=LETTER)

    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='MyHeading1', parent=styles['Heading1'], fontSize=18, spaceAfter=10))
    styles.add(ParagraphStyle(name='MyHeading2', parent=styles['Heading2'], fontSize=14, spaceAfter=6, spaceBefore=12))
    styles.add(ParagraphStyle(name='MyHeading3', parent=styles['Heading3'], fontSize=12, spaceAfter=4, spaceBefore=10))
    styles.add(ParagraphStyle(name='MyHeading4', parent=styles['Heading4'], fontSize=8, spaceAfter=4, spaceBefore=10))
    styles.add(ParagraphStyle(name='MyHeading5', parent=styles['Heading5'], fontSize=7, spaceAfter=4, spaceBefore=10))
    
    story = []

    # Title and Project URL
    story.append(Paragraph(metadata["attributes"]["title"], styles["MyHeading1"]))
    story.append(Paragraph(f"Project URL: <a href='{project_url}'>{project_url}</a>", styles["Normal"]))

    # QR Code
    qr_img_io = generate_qr_code(project_url)  # Returns BytesIO
    qr_img_io.seek(0)

    # For the body of the PDF — use BytesIO
    story.append(RLImage(qr_img_io, width=1.5 * inch, height=1.5 * inch))
    story.append(Spacer(1, 12))

    # For page footer — wrap in ImageReader
    project_qrcode = ImageReader(qr_img_io)
    story.append(Spacer(1, 12))

    # Metadata Sections
    render_metadata_section(metadata, story, styles, timestamp)
    render_contributors_section(contributors, story, styles)
    story.append(PageBreak())
    render_file_table(fetch_files(project_id), story, styles, "Files in Main Project")
    render_wiki_section(project_id, story, styles)

    # Components
    story.append(Paragraph("5. Components and Their Files", styles["MyHeading2"]))
    for comp in components:
        title = comp["attributes"]["title"]
        comp_id = comp["id"]
        comp_url = comp["links"]["html"]

        story.append(Paragraph(title, styles["MyHeading3"]))
        story.append(Paragraph(f"Component URL: <a href='{comp_url}'>{comp_url}</a>", styles["Normal"]))
        render_file_table(fetch_files(comp_id), story, styles)

    # Add Page Number and QR on all pages
    add_page_func = partial(add_page_number, timestamp=timestamp, project_qrcode=project_qrcode)
    doc.build(story, onFirstPage=add_page_func, onLaterPages=add_page_func)

    return output_path