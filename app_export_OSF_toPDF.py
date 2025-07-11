'''
## =================================================================================================
## Title: Streamlit App to Download OSF Project to PDF                                            ##
## Project:                                                                                       ##
##      Export OSF Project to PDF - Centre for Open Science (CoS) & University of Manchester (UoM)##
## UoM Team:                                                                                      ##
##      Ramiro Bravo, Sarah Jaffa, Benito Matischen                                               ##
## Author(s):                                                                                     ##
##       Ramiro Bravo - ramiro.bravo@manchester.ac.uk - ramirobravo@gmail.com                     ##
## Create date:                                                                                   ##
##       July-2025                                                                                ##
## Description:                                                                                   ##
##      The Streamlit app serves as the front end application allowing users to download OSF      ##
##      project in PDF format.                                                                    ##
## Parameters:                                                                                    ##
##      OSF Project URL: Provide the URL of the project fro exapmle: https://osf.io/kzc68/        ##
##      Select API environment: Production or Test                                                ##
##      Token Source: Provided via .env file or entering the OSF API token.                       ##
##      OSF API Key: Allows users to enter (paste) the API key for private repositories           ##
## Running App locally: Recomended to use a python virtual environment                            ##
##    $ source ./venv/bin/activate                                                                ##
##    $ streamlit run app_export_OSF_toPDF.py                                                     ##
##                                                                                                ##
## =================================================================================================
'''

import streamlit as st
from pdf_generator import build_pdf
import os
import tempfile
from datetime import datetime


#page configuration
st.set_page_config(page_title="Export & Download OSF project to PDF",
                   #page_icon=":outbox_tray:",
                   page_icon=":arrow_down:",
                   layout="centered")

#REMOVE THE SETTING OPTIONS
st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True)


st.title("📄 OSF Project PDF Exporter")

# Input fields
url = None
url = st.text_input("Enter OSF Project URL:", max_chars=30)
if url!="":
    osf_id = url.split(".io/")[1].strip("/")
    st.write(osf_id)


api_choice = st.radio("Select API Environment:", ["Production", "Test"])
is_test = True if api_choice == "Test" else False


st.subheader("🔐 OSF Project type")
project_type = st.radio("Choose project visibility: ", ["Public", "Private"])

osf_token = None
if project_type == "Private":
    # Token input
    st.subheader("🔑 OSF Token")
    token_source = st.radio("Choose token source:", ["Paste token manually", "Use .env file"])

    if token_source == "Paste token manually":
        osf_token = st.text_input("Enter your OSF API token:", type="password")
    else:
        from dotenv import load_dotenv
        load_dotenv()
        osf_token = os.getenv("OSF_TOKEN")

st.write(osf_token)

# Output folder
output_dir = "exported_pdfs"
os.makedirs(output_dir, exist_ok=True)

if st.button("Generate PDF"):
    if osf_id.strip() == "":
        st.warning("Please enter a valid OSF Project ID.")
#    elif not osf_token:
#        st.warning("API token is required.")
    else:
        #output_path = os.path.join(output_dir, f"osf_export_{osf_id}.pdf")
        #if output_path is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"OSF_Project_{osf_id}_exported_{timestamp}.pdf"
        output_path = os.path.join(output_dir,file_name)
        #output_path = os.path.join(output_dir,f"OSF_Project_{osf_id}_exported_{timestamp}.pdf")
        #output_path = f"OSF_Full_Metadata_Project_{project_id}.pdf"
        st.write(output_path)  # just to verify the output

        try:
            with st.spinner("Generating PDF..."):
                result = build_pdf(osf_id, is_test, output_path=output_path, api_token=osf_token, project_type=project_type)
                #result = build_pdf(osf_id, is_test, output_path=output_path, api_token=osf_token)
            st.success(f"PDF generated and saved to: {result}")
            st.balloons()
            with open(result, "rb") as file:
                st.download_button(
                    label=f"📥 Download PDF - {file_name}",
                    data=file,
                    #file_name=f"osf_export_{osf_id}.pdf",
                    file_name=file_name,
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Error generating PDF: {e}")
