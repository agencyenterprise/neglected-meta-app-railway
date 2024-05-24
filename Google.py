import pickle
import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import datetime
import os
import io
from googleapiclient.http import MediaIoBaseDownload
import shutil
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


CLIENT_SECRET_FILE = "secret_file.json"
API_NAME = "drive"
API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def create_and_download_files():
    if not os.path.exists("secret_file.json"):
        with open("secret_file.json", "w") as f:
            json.dump(
                {
                    "type": "service_account",
                    "project_id": "sage-wave-424300-f0",
                    "private_key_id": os.environ.get("PRIVATE_KEY_ID"),
                    "private_key": os.environ.get("PRIVATE_KEY").replace("\\n", "\n")
                    "client_email": "railway@sage-wave-424300-f0.iam.gserviceaccount.com",
                    "client_id": "112563351930272270885",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/railway%40sage-wave-424300-f0.iam.gserviceaccount.com",
                    "universe_domain": "googleapis.com",
                },
                f,
            )
    # check to see if the files are already downloaded
    if os.path.exists("app_files") and os.path.exists("lw_data"):
        return
    file_ids = [
        "1cyyNMD5wj53mc_cMLfL8VoTHVWDdO1Z7",
        "1nfiT_8YptIsTobWewZ--miOOYdOgSu-O",
    ]
    file_paths = ["app_files.zip", "lw_data.zip"]
    download_files(file_ids, file_paths)
    for fp in file_paths:
        shutil.unpack_archive(
            filename=fp,  # Path to the archive file
            extract_dir=".",  # Destination directory for extraction
            format=None,  # Optional: Specify the archive format if it's not detected automatically
        )


def download_files(file_ids, file_paths):
    API_NAME = "drive"
    API_VERSION = "v3"
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    # Path to your service account key file
    KEY_FILE_LOCATION = "secret_file.json"

    # Create the service
    service = create_service(API_NAME, API_VERSION, SCOPES, KEY_FILE_LOCATION)
    for fid, fp in zip(file_ids, file_paths):
        request = service.files().get_media(fileId=fid)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))
        fh.seek(0)
        with open(fp, "wb") as f:
            f.write(fh.read())
            f.close()
    print("Done")


def create_service(api_name, api_version, scopes, key_file_location):
    credentials = Credentials.from_service_account_file(
        key_file_location, scopes=scopes
    )
    service = build(api_name, api_version, credentials=credentials)
    return service


def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
    dt = datetime.datetime(year, month, day, hour, minute, 0).isoformat() + "Z"
    return dt
