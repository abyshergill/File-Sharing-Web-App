# 📁 File Sharing Web App

A simple **Streamlit-based web app** to upload and share files using randomly generated access codes — no email or direct file sharing links needed.

---

## 🚀 Features

- **Upload Files**: Generate a **unique code** for each uploaded file.
- **Download Files**: Retrieve files by entering the correct code.
- **Secure Access**: Only those with the code can download the file.
- **Simple UI**: Easy-to-use navigation with `Home`, `Upload`, and `Download` options.

---

## 📌 How It Works

### 🏠 Home

- Provides an overview and instructions on using the app.

### 📤 Upload

1. Upload a file.
2. The app will generate a **uuid.uuid4() code** (uppercase letters + digits).
3. You’ll receive a message displaying your unique code.
4. **Save this code!** It’s required to download the file later.

### 📥 Download

1. Enter the code you received when uploading the file.
2. If a matching file exists, a **download button** will appear.
3. Click the button to retrieve the file.
5. In case you type wrong code you will get total 10 attempts to download the file.
6. With Each attempt writing the code inside the text input increase by 5 seconds from previous

---

## 🛠️ How to Run the App

### 🔧 Step 1: Clone the Repository

```bash
git clone https://github.com/abyshergill/File-Sharing-Web-App.git
cd File-Sharing-Web-App
```
### 📦 Step 2: Install Dependencies Using requirements.txt

```bash
pip install -r requirements.txt
```
▶️ Step 3: Run the Streamlit App

Make sure your main file is named main.py, then run:

```bash
streamlit run main.py
```

📂 Project Structure

```bash
File-Sharing-Web-App/
├── main.py              # Main Streamlit app
├── file_record_db/      # Database directory for sqlite 
├      └── records.db    # Database create after your first run
├── records/             # Utility folder for database operation
├      └── __init__.py
├      └── records.py
├── uploaded_files/      # Folder to store uploaded files
├── requirements.txt     # List of Python dependencies
└── README.md            # This file
└── license.txt
```
🔒 Security Note
* This app stores uploaded files in a local folder (uploaded_files/).
* File access is controlled via random code generation.
* SQLite database or persistent storage is used for code mapping inside the uploaded_files directory.

📜 License
MIT License | Author : shergillkuldeep@outlook.com 