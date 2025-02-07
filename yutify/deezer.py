import os
import sys
from pprint import pprint

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.cheap_utils import cheap_compare


class Deezer:
    def __init__(self) -> None:
        self.music_info = []
        self._session = requests.Session()
        self.api_url = "https://api.deezer.com"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close_session()

    def __del__(self) -> None:
        """Ensure session closes when instance is deleted."""
        self.close_session()

    def close_session(self) -> None:
        """Close the session when no longer needed."""
        self._session.close()

    def search(self, artist: str, song: str) -> dict | None:
        """Search Deezer's music catalogue.

        Args:
            artist (str): Artist(s) name.
            song (str): Song name.

        Returns:
            dict | None: Dictionary containing music info or `None`.
        """
        self.music_info = []

        search_types = ["track", "album"]
        for search_type in search_types:
            if self.music_info:
                return self.music_info[0]

            endpoint = f"{self.api_url}/search/{search_type}"
            query = f'?q=artist:"{artist}" {search_type}:"{song}"&limit=10'
            query_url = endpoint + query

            response = self._session.get(query_url, timeout=30)
            if response.status_code != 200:
                return None

            try:
                result = response.json()["data"]
            except IndexError:
                continue

            self._parse_results(artist, song, result)

        if self.music_info:
            return self.music_info[0]
        return None

    def get_upc_isrc(self, music_id: int, music_type: str) -> dict | None:
        """Return ISRC or UPC for a track or album respectively and release date!

        Args:
            id (int): Deezer track or album ID.
            type (str): Whether it's a `track` or an `album`.

        Returns:
            str | None: Return ISRC or UPC if found, otherwise return None.
        """
        match music_type:
            case "track":
                query_url = f"{self.api_url}/track/{music_id}"
                response = self._session.get(query_url, timeout=30)
                if response.status_code != 200:
                    return None

                result = response.json()
                return {
                    "isrc": result["isrc"],
                    "release_date": result["release_date"],
                    "tempo": result["bpm"] if result["bpm"] else None,
                }

            case "album":
                query_url = f"{self.api_url}/album/{music_id}"
                response = self._session.get(query_url, timeout=30)

                if response.status_code != 200:
                    return None

                result = response.json()
                return {
                    "genre": result["genres"]["data"][0]["name"],
                    "release_date": result["release_date"],
                    "upc": result["upc"],
                }

            case _:
                return None

    def _parse_results(self, artist: str, song: str, results: list[dict]) -> None:
        """Helper function to parse results returned by Deezer API.

        Args:
            artist (str): Artist name(s)
            song (str): Song name
            results (list[dict]): Returned by `self.search()`.

        Returns:
            None: Modify instance variable `self.music_info`.
        """
        for result in results:
            if self.music_info:
                return

            if not (
                cheap_compare(result["title"], song)
                and cheap_compare(result["artist"]["name"], artist)
            ):
                continue

            match result["type"]:
                case "track":
                    track_info = self.get_upc_isrc(result["id"], result["type"])
                    genre = None
                    isrc = track_info["isrc"]
                    release_date = track_info["release_date"]
                    tempo = track_info.get("tempo")
                    upc = None

                case "album":
                    album_info = self.get_upc_isrc(result["id"], result["type"])
                    genre = album_info.get("genre")
                    isrc = None
                    release_date = album_info["release_date"]
                    tempo = None
                    upc = album_info["upc"]

            try:
                album_type = (
                    result["type"]
                    if result["title"] == result["album"]["title"]
                    else result["album"]["type"]
                )
            except KeyError:
                album_type = result["record_type"]

            self.music_info.append(
                {
                    "album_art": (
                        result["album"]["cover_xl"]
                        if result["type"] == "track"
                        else result["cover_xl"]
                    ),
                    "album_title": (
                        result["album"]["title"]
                        if result["type"] == "track"
                        else result["title"]
                    ),
                    "album_type": album_type,
                    "artists": result["artist"]["name"],
                    "genre": genre,
                    "id": result["id"],
                    "isrc": isrc,
                    "lyrics": None,
                    "release_date": release_date,
                    "tempo": tempo,
                    "title": result["title"],
                    "type": result["type"],
                    "upc": upc,
                    "url": result["link"],
                }
            )


if __name__ == "__main__":
    deezer = Deezer()

    try:
        artist_name = input("Artist Name: ")
        song_name = input("Song Name: ")
        pprint(deezer.search(artist_name, song_name))
    finally:
        deezer.close_session()
