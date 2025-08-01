import streamlit as st
import tempfile
import os
import pdb
import osfexport
#from exporter_pdf_for_streamlit import write_pdf, get_project_data
#pip install -e osfio-export-tool

st.set_page_config(page_title="OSF PDF Export Tool", layout="centered")

st.title("🔄 OSF Project to PDF")

project_type = None
project_type = st.radio("Select Project Type:", ["Public", "Private"])

project_url = st.text_input("📁 Enter OSF Project URL:", placeholder="e.g. https://osf.io/abcde/")
#select Public or private project
st.subheader("🔐 OSF Project type")
#project_type = st.radio("Choose project visibility: ", ["Public", "Private"])
if project_type == "Private":
    # Token input
    st.subheader("🔑 OSF Token")
    pat = st.text_input("Enter your OSF API token:", type="password")
else:
    st.info("Public projects do not require a token.")
    pat = ''  # Needs to be empty string not None to avoid errors

# --- Form input section ---
with st.form("export_form"):
    # project_id = st.text_input("📁 Enter OSF Project URL:", placeholder="e.g. https://osf.io/abcde/")
    # #select Public or private project
    # st.subheader("🔐 OSF Project type")
    # #project_type = st.radio("Choose project visibility: ", ["Public", "Private"])
    # project_type = st.radio("Select Project Type:", ["Public", "Private"])
    # if project_type == "Private":
    #     # Token input
    #     st.subheader("🔑 OSF Token")
    #     pat = st.text_input("Enter your OSF API token:", type="password")
    # else:
    #     st.info("Public projects do not require a token.")
    #     pat = None

    # osf_token = None
    # if project_type == "Private":
    #     # Token input
    #     st.subheader("🔑 OSF Token")
    #     token_source = st.radio("Choose token source:", ["Paste token manually", "Use .env file"])

    #     if token_source == "Paste token manually":
    #         osf_token = st.text_input("Enter your OSF API token:", type="password")
    #     else:
    #         from dotenv import load_dotenv
    #         load_dotenv()
    #         osf_token = os.getenv("OSF_TOKEN")    
    
    #dryrun = st.checkbox("Use test/mock data (Dry run)?", value=True)
    #usetest = st.checkbox("Use OSF Test API?", value=False)
    dryrun = False  # For testing purposes, set to True
    usetest = False

    submitted = st.form_submit_button("Export to PDF")

if submitted:
    if not pat and not dryrun and project_type == "Private":
        st.warning("Please provide a Personal Access Token unless using dry run mode.")
    else:
        with st.spinner("Generating PDF... Please wait."):
            # Step 1: Get project data
            try:
                #pdb.set_trace()
                # Extract ID from URL
                project_id = osfexport.extract_project_id(project_url)

                projects, root_nodes = osfexport.get_project_data(
                    pat=pat,
                    dryrun=dryrun,
                    project_id=project_id,
                    usetest=usetest
                )

                if not root_nodes:
                    st.error("No root projects found.")
                else:
                    root_idx = root_nodes[0]  # Export first root node

                # Step 2: Generate the PDF to a temp folder
                with tempfile.TemporaryDirectory() as tmpdir:
                    pdf_obj, pdf_path = osfexport.write_pdf(
                        projects,
                        root_idx=root_idx,
                        folder=tmpdir
                    )

                    # Step 3: Display the download link
                    with open(pdf_path, "rb") as f:
                        st.success("✅ PDF Generated!")
                        st.download_button(
                            label="📄 Download PDF",
                            data=f,
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf"
                        )
            except KeyError as e:
                st.write("Invalid project ID. Please try again.")
