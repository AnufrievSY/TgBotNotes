import re
from yandex_music import Client

TRACK_RE = re.compile(r"/track/(\d+)")
ALBUM_TRACK_RE = re.compile(r"/album/(\d+)/track/(\d+)")


def extract_track_id(url: str) -> int | None:
    m = TRACK_RE.search(url)
    if m:
        return int(m.group(1))

    m = ALBUM_TRACK_RE.search(url)
    if m:
        return int(m.group(2))

    return None


def get_track_meta(url: str, token: str=None) -> tuple[str, str] | None:
    track_id = extract_track_id(url)
    if not track_id:
        return None

    client = Client(token).init()
    track = client.tracks([track_id])[0]

    title = track.title
    artist = ", ".join(a.name for a in track.artists) if track.artists else "Unknown"

    return artist, title


if __name__ == "__main__":
    print(get_track_meta('https://music.yandex.ru/album/474096/track/35487142?ref_id=336D5361-BECC-4F18-9777-95767EB09DF4&utm_medium=copy_link'))