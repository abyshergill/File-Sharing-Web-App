import streamlit as st
import os
import random
import string


UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Dictionary to map codes to file paths (in-memory)
code_to_file = {}

# function to generate unique code
def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=69))

# Navbar options
nav_options = ["Home", "Upload", "Download"]

# Create navbar-like selection
selected_nav = st.radio("Navigation", nav_options, index=1, horizontal=True)

if selected_nav == "Home":
    st.title("Welcome to the File Upload and Download App")
    st.markdown("""
                ## Introduction :
                * File sharing project get rid of Email hyperlink paths to check and download the files.
                * Original file can only be download if you have random number of that file after upload. 
                * This project work similar like sharing permission to some specific people but instead of sharing it use number to link your file.
                ## Instruction Manual:
                * **Upload :** In this option, Upload your file it will **file code ( generate random number )** which will allow you to download the file. 
                * **Download :** In this option, Download file if you have **file code  ( random number )** related to your upload file.
                """)
    
elif selected_nav == "Upload":
    st.title("📤 Upload a File")
    uploaded_file = st.file_uploader("Choose a file to upload")

    if uploaded_file is not None:
        # Generate a random code
        code = generate_unique_code()
        file_path = os.path.join(UPLOAD_DIR, f"{code}_{uploaded_file.name}")
        
        # Save the uploaded file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Save mapping
        code_to_file[code] = file_path
        
        st.success(f"✅ File uploaded successfully!")
        st.info(f"Your download code is: `{code}`")
        st.warning("Make sure to save this code to download the file later.")

elif selected_nav == "Download":
    st.title("📥 Download a File")
    code_input = st.text_input("Enter your file code")

    if code_input:
        matched_files = [f for f in os.listdir(UPLOAD_DIR) if f.startswith(code_input + "_")]
        if matched_files:
            file_path = os.path.join(UPLOAD_DIR, matched_files[0])
            file_name = matched_files[0].split("_", 1)[1]

            with open(file_path, "rb") as f:
                st.download_button(label="⬇️ Download File",
                                   data=f,
                                   file_name=file_name,
                                   mime="application/octet-stream")
        else:
            st.error("❌ Invalid code or file not found.")
