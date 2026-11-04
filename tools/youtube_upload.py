#!/usr/bin/env python3
"""Upload a rendered MP4 to YouTube using OAuth user credentials."""

import argparse
import os
from pathlib import Path

# Google client libraries are imported lazily inside the functions below so that
# tool discovery (make preflight) works in environments that lack them.

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_FILE = Path(
    os.environ.get("YOUTUBE_CLIENT_SECRET", "credentials/client_secret.json")
)
TOKEN_FILE = Path(
    os.environ.get("YOUTUBE_TOKEN_FILE", "credentials/youtube_token.json")
)


def get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_FILE.exists():
                raise FileNotFoundError(
                    f"OAuth client JSON bulunamadı: {CLIENT_FILE}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_FILE), SCOPES
            )
            creds = flow.run_local_server(
                host="127.0.0.1",
                port=0,
                authorization_prompt_message="Tarayıcı açılıyor. Google hesabınla giriş yapıp izin ver.",
                success_message="Yetkilendirme tamamlandı. Bu sekmeyi kapatabilirsin.",
                open_browser=True,
            )

        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())

    return creds


def upload_video(path, title, description, privacy):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    video_path = Path(path).expanduser().resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"Video bulunamadı: {video_path}")

    youtube = build("youtube", "v3", credentials=get_credentials())

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(
            str(video_path), mimetype="video/mp4", resumable=True
        ),
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Yükleme: %{int(status.progress() * 100)}")

    print("Video ID:", response["id"])
    print("YouTube URL: https://www.youtube.com/watch?v=" + response["id"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="private",
    )
    args = parser.parse_args()

    upload_video(args.video, args.title, args.description, args.privacy)
