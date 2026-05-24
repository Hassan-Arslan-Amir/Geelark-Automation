import os
import io
import sys
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Allow importing supabase_logger from the parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_logger import get_content_status

# ============================================================
# CONFIGURATION — Only edit this section
# ============================================================
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CLIENT_FOLDER_ID = "1brd_LYl-ixvWF-r0gCk1PYCpjdTANEay"
BASE_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ugc_videos")
# ============================================================

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOKEN_PATH = os.path.join(_SCRIPT_DIR, 'token.json')
_CREDS_PATH = os.path.join(_SCRIPT_DIR, 'credentials.json')


def authenticate():
    """Login to Google and return Drive service."""
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
    """Try to extract a date from the folder name regardless of format."""
    date_part = folder_name.split(' ')[0]

    formats = [
        "%d-%m-%Y",
        "%d-%m-%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue

    return None


def get_subfolders(service, parent_folder_id):
    """Get all date-named subfolders inside the client's folder."""
    results = service.files().list(
        q=f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        orderBy="name"
    ).execute()

    return results.get('files', [])


def get_files_in_folder(service, folder_id):
    """Get all video and image files inside a given folder."""
    results = service.files().list(
        q=f"'{folder_id}' in parents and (mimeType contains 'video/' or mimeType contains 'image/') and trashed=false",
        fields="files(id, name, size, mimeType)"
    ).execute()

    return results.get('files', [])


def sanitize_filename(file_name: str) -> str:
    """Replace characters that are illegal in Windows file paths."""
    # Windows illegal characters: \ / : * ? " < > |
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        file_name = file_name.replace(ch, '-')
    return file_name


def to_content_key(file_path: str) -> str:
    """Return a machine-independent content key: path relative to ugc_videos/ with forward slashes.
    Example: 'E:\\...\\ugc_videos\\21-05-26 Kit\\video.mp4' → '21-05-26 Kit/video.mp4'
    """
    return os.path.relpath(file_path, BASE_DOWNLOAD_DIR).replace('\\', '/')


def download_file(service, file_id, file_name, download_path):
    """Download a single video file to the given path."""
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
        return True

    except Exception as e:
        print(f"  ❌ Failed to download {file_name}: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return False

def main():
    print("=" * 50)
    print("   UGC Video Downloader — Today Only")
    print("=" * 50)

    # Today's date
    today = datetime.now().date()
    print(f"\n📅 Today's date: {today.strftime('%d-%m-%Y')}\n")

    # Step 1: Authenticate
    print("🔐 Authenticating with Google Drive...")
    service = authenticate()
    print("✅ Authentication successful!\n")

    # Step 2: Get all subfolders
    print("📂 Fetching folders from client's Drive...")
    subfolders = get_subfolders(service, CLIENT_FOLDER_ID)

    if not subfolders:
        print("❌ No folders found! Check if the folder ID is correct.")
        return

    # Step 3: Filter only today's folders
    todays_folders = []
    for folder in subfolders:
        folder_date = parse_folder_date(folder['name'])
        if folder_date == today:
            todays_folders.append(folder)

    if not todays_folders:
        print(f"⚠️  No folders found for today ({today.strftime('%d-%m-%Y')})")
        print("    Your client may not have uploaded content yet.")
        return

    print(f"✅ Found {len(todays_folders)} folder(s) for today:\n")
    for f in todays_folders:
        print(f"   📁 {f['name']}")
    print()

    # Step 4: Download ONE new file per run
    download_happened = False
    downloaded_file_path = None
    folder_was_empty = True
    all_already_downloaded = False

    for folder in todays_folders:
        if download_happened:
            break

        print(f"📁 Folder: {folder['name']}")
        files = get_files_in_folder(service, folder['id'])

        if not files:
            print(f"   ⚠️  Folder is empty — no files uploaded yet.\n")
            continue

        folder_was_empty = False
        print(f"   🎬 Found {len(files)} file(s) — videos & images\n")
        folder_download_path = os.path.join(BASE_DOWNLOAD_DIR, folder['name'])

        all_skipped = True
        for file in files:
            file_path = os.path.join(folder_download_path, sanitize_filename(file['name']))

            status = get_content_status(to_content_key(file_path))

            if status == "posted":
                print(f"  ⏭  Skipping (already posted): {file['name']}")
                continue

            all_skipped = False

            if status == "not_posted" and os.path.exists(file_path):
                # File was downloaded before but posting was interrupted — reuse it
                print(f"  ♻️  Reusing unposted file: {file['name']}")
                downloaded_file_path = file_path
                download_happened = True
                break

            # status == "not_found" or file missing on disk — download it
            success = download_file(service, file['id'], file['name'], folder_download_path)
            if success:
                downloaded_file_path = file_path
                download_happened = True
                break

        if all_skipped:
            all_already_downloaded = True

    # Step 5: Final message
    print()
    print("=" * 50)
    if download_happened:
        print("   ✅ 1 file downloaded successfully!")
        print("   ▶  Run the script again to download the next one.")
    elif folder_was_empty:
        print("   ⚠️  Today's folder exists but is empty.")
        print("       Your client has not uploaded any content yet.")
    elif all_already_downloaded:
        print("   ✅ All files for today are already downloaded!")
        print("       No new content to process.")
    print(f"   📅 Date: {today.strftime('%d-%m-%Y')}")
    print("=" * 50)
    print("\n🎉 Done!\n")

    return downloaded_file_path

if __name__ == '__main__':
    main()
