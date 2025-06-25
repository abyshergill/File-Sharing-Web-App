import streamlit as st
import os

import uuid   
import string
import time

from records.records import create_records_db
from records.records import get_file_info_by_code

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def initiate_download(uuid_code):
    file_info = get_file_info_by_code(uuid_code)
    if file_info is not None:
        matched_files = [f for f in os.listdir(UPLOAD_DIR) if f.startswith(uuid_code + "_")]
        file_path = os.path.join(UPLOAD_DIR, matched_files[0])
        file_name = matched_files[0].split("_", 1)[1]
        with open(file_path, "rb") as f:
            st.download_button(label="⬇️ Download File",
                                data=f,
                                file_name=file_name,
                                mime="application/octet-stream")
    else:
        st.error("No File Found")
    
    

nav_options = ["Home", "Upload", "Download"]

selected_nav = st.radio("Navigation", nav_options, index=1, horizontal=True)

if selected_nav == "Home":
    st.title("Welcome to the File Sharing Web App")
    st.markdown("""
                ## Introduction :
                * File sharing project get rid of Email hyperlink paths to check and download the files.
                * Original file can only be download if you have random number of that file after upload. 
                * This project work similar like sharing permission to some specific people but instead of sharing it use number to link your file.
                ## Instruction Manual:
                * **Upload :** In this option, Upload your file it will **file code ( generate random number )** which will allow you to download the file. 
                * **Download :** In this option, Download file if you have **file code  ( random number )** related to your upload file.
                ## Note :
                - With Each Wrong attempt to download the file, Try time will increase by 5 seconds from preivous.
                - You will get total 10 attempts to try download.
                        ==== :D Although with refresh you can again try to downlaod with itme increase. 
                """)
    
elif selected_nav == "Upload":
    st.title("📤 Upload a File")
    uploaded_file = st.file_uploader("Choose a file to upload")
    if uploaded_file is not None:
        code = uuid.uuid4()   
        file_path = os.path.join(UPLOAD_DIR, f"{code}_{uploaded_file.name}")
        recorded_data = (code, uploaded_file.name, UPLOAD_DIR)
        create_records_db(recorded_data)    
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"✅ File uploaded successfully!")
        st.info(f"Your download code is: `{code}`")
        st.warning("Make sure to save this code to download the file later.")

if 'download_attempts' not in st.session_state:
    st.session_state.download_attempts = 0
if 'download_delay' not in st.session_state:
    st.session_state.download_delay = 2 
if 'last_attempt_time' not in st.session_state:
    st.session_state.last_attempt_time = 0

elif selected_nav == "Download":
    st.title("📥 Download a File")
    if 'error_message' in st.session_state and st.session_state.error_message:
        st.error(st.session_state.error_message)
        st.session_state.error_message = "" 
    
    if st.session_state.download_attempts >= 10:
        st.error("You have completed the maximum attempt limit. Please refresh the page to try again.")
    else:
        code_input = st.text_input("Enter your file code", key="download_code_input")
        if code_input:
            current_time = time.time()
            if current_time - st.session_state.last_attempt_time < st.session_state.download_delay:
                st.warning(f"Please wait {int(st.session_state.download_delay - (current_time - st.session_state.last_attempt_time))} seconds before trying again.")
            else:
                st.session_state.current_code_input = code_input
                found, database_information  = get_file_info_by_code(st.session_state.current_code_input)
                if found:
                    st.success("✅ Code found! Preparing download...")
                    st.session_state.download_attempts = 0
                    st.session_state.download_delay = 2
                    st.session_state.last_attempt_time = 0
                    st.session_state.error_message = "" 
                    initiate_download(st.session_state.current_code_input)
                else:
                    st.session_state.download_attempts += 1
                    st.session_state.last_attempt_time = current_time
                    st.session_state.download_delay = min(st.session_state.download_delay + 5, 60)                
                    if st.session_state.download_attempts >= 10:
                        st.session_state.error_message = "You have completed the maximum attempt limit. Please refresh the page to try again."
                    else:
                        st.session_state.error_message = f"❌ Invalid code. You have {10 - st.session_state.download_attempts} attempts left. Please wait {st.session_state.download_delay} seconds."                   
                    st.rerun() 
