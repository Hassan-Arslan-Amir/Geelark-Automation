import os
import io
import re
import sys
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_logger import get_content_status

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CLIENT_FOLDER_ID = "1brd_LYl-ixvWF-r0gCk1PYCpjdTANEay"
BASE_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ugc_videos")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOKEN_PATH = os.path.join(_SCRIPT_DIR, 'token.json')
_CREDS_PATH = os.path.join(_SCRIPT_DIR, 'credentials.json')

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def parse_drive_folder_id(drive_url: str) -> str:
    """Extract a Google Drive folder ID from a sharing URL."""
    if not drive_url or not drive_url.strip():
        raise ValueError("Google Drive URL is not configured in Settings.")

    url = drive_url.strip()
    match = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)

    if re.fullmatch(r"[a-zA-Z0-9_-]{10,}", url):
        return url

    raise ValueError(f"Could not parse Google Drive folder ID from: {drive_url}")


def authenticate():
    creds = None
    if os.path.exists(_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(_CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def parse_folder_date(folder_name):
    date_part = folder_name.split(' ')[0]
    for fmt in ("%d-%m-%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue
    return None


def get_subfolders(service, parent_folder_id):
    results = service.files().list(
        q=f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        orderBy="name",
    ).execute()
    return results.get('files', [])


def get_latest_dated_folder(subfolders: list) -> dict | None:
    """Pick the subfolder with the most recent parseable date in its name."""
    dated = []
    for folder in subfolders:
        folder_date = parse_folder_date(folder['name'])
        if folder_date:
            dated.append((folder_date, folder))

    if not dated:
        return subfolders[-1] if subfolders else None

    dated.sort(key=lambda x: x[0], reverse=True)
    return dated[0][1]


def get_files_in_folder(service, folder_id, media_type: str):
    if media_type == "video":
        mime_filter = "mimeType contains 'video/'"
    elif media_type == "image":
        mime_filter = "mimeType contains 'image/'"
    else:
        mime_filter = "(mimeType contains 'video/' or mimeType contains 'image/')"

    results = service.files().list(
        q=f"'{folder_id}' in parents and {mime_filter} and trashed=false",
        fields="files(id, name, size, mimeType)",
    ).execute()
    return results.get('files', [])


def sanitize_filename(file_name: str) -> str:
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        file_name = file_name.replace(ch, '-')
    return file_name


def to_content_key(file_path: str) -> str:
    return os.path.relpath(file_path, BASE_DOWNLOAD_DIR).replace('\\', '/')


def download_file(service, file_id, file_name, download_path):
    os.makedirs(download_path, exist_ok=True)
    file_name = sanitize_filename(file_name)
    file_path = os.path.join(download_path, file_name)

    print(f"  ⬇  Downloading: {file_name}")

    try:
        request = service.files().get_media(fileId=file_id)
        with io.FileIO(file_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request, chunksize=50 * 1024 * 1024)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"     Progress: {int(status.progress() * 100)}%")
        print(f"  ✅ Downloaded: {file_name}")
        return file_path
    except Exception as e:
        print(f"  ❌ Failed to download {file_name}: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None


def download_content(drive_url: str, media_type: str) -> str | None:
    """
    Download one eligible file from the latest dated folder on Google Drive.

    drive_url   : Full Google Drive folder URL from bot_settings
    media_type  : 'video' or 'image'
    Returns     : Local file path, or None if nothing available
    """
    folder_id = parse_drive_folder_id(drive_url)

    print("=" * 50)
    print(f"   UGC Downloader — latest folder ({media_type})")
    print("=" * 50)

    print("\n🔐 Authenticating with Google Drive...")
    service = authenticate()
    print("✅ Authentication successful!\n")

    print("📂 Fetching folders from Drive...")
    subfolders = get_subfolders(service, folder_id)
    if not subfolders:
        print("❌ No folders found. Check the Google Drive URL in Settings.")
        return None

    latest = get_latest_dated_folder(subfolders)
    if not latest:
        print("❌ Could not determine latest folder.")
        return None

    print(f"📁 Latest folder: {latest['name']}\n")
    files = get_files_in_folder(service, latest['id'], media_type)

    if not files:
        print(f"   ⚠️  No {media_type} files in this folder.")
        return None

    print(f"   🎬 Found {len(files)} matching {media_type} file(s)\n")
    folder_download_path = os.path.join(BASE_DOWNLOAD_DIR, latest['name'])

    for file in files:
        file_path = os.path.join(folder_download_path, sanitize_filename(file['name']))
        status = get_content_status(to_content_key(file_path))

        if status == "posted":
            print(f"  ⏭  Skipping (already posted): {file['name']}")
            continue

        if status == "not_posted" and os.path.exists(file_path):
            print(f"  ♻️  Reusing unposted file: {file['name']}")
            return file_path

        downloaded = download_file(service, file['id'], file['name'], folder_download_path)
        if downloaded:
            return downloaded

    print("\n⚠️  No new content available — all matching files are already posted.")
    return None


def main():
    """Legacy entry: download from hardcoded folder, today only, any media type."""
    print("=" * 50)
    print("   UGC Video Downloader — Today Only (legacy)")
    print("=" * 50)

    today = datetime.now().date()
    print(f"\n📅 Today's date: {today.strftime('%d-%m-%Y')}\n")

    service = authenticate()
    subfolders = get_subfolders(service, CLIENT_FOLDER_ID)

    todays_folders = [f for f in subfolders if parse_folder_date(f['name']) == today]
    if not todays_folders:
        print(f"⚠️  No folders found for today ({today.strftime('%d-%m-%Y')})")
        return None

    for folder in todays_folders:
        files = get_files_in_folder(service, folder['id'], "video")
        files += get_files_in_folder(service, folder['id'], "image")
        folder_download_path = os.path.join(BASE_DOWNLOAD_DIR, folder['name'])

        for file in files:
            file_path = os.path.join(folder_download_path, sanitize_filename(file['name']))
            status = get_content_status(to_content_key(file_path))

            if status == "posted":
                continue
            if status == "not_posted" and os.path.exists(file_path):
                return file_path

            downloaded = download_file(service, file['id'], file['name'], folder_download_path)
            if downloaded:
                return downloaded

    return None


if __name__ == '__main__':
    main()
