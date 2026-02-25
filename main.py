import requests
from urllib.parse import quote
import conf
import webbrowser
import http.server
import socketserver
import threading
import urllib.parse
import unicodedata
import re
import random


PORT = 7000
REDIRECT_URL = f"http://127.0.0.1:{PORT}"
PLAYLIST_ID = "0uM9ZZIgYvyutul9RmEq22"
PLAYLIST_URI = f"spotify:playlist:{PLAYLIST_ID}"
SCOPE = "user-modify-playback-state user-read-currently-playing user-read-playback-state playlist-modify-public playlist-modify-private playlist-read-private"


def auth_url():
    base_url = "https://accounts.spotify.com/authorize"
    response_type = "code"
    client_id = conf.client_id

    url = f"{base_url}?"
    url += f"response_type={quote(response_type)}"
    url += f"&client_id={quote(client_id)}"
    url += f"&scope={quote(SCOPE)}"
    url += f"&redirect_uri={quote(REDIRECT_URL, safe='')}"

    return url


class AuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            self.server.code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>You may close this window now.</h1>")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging to keep output clean
        return

def get_auth_code():
    handler = AuthHandler
    httpd = socketserver.TCPServer(("", PORT), handler)

    # Run the server in a separate thread
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()

    # Open the browser for the user to authorize
    webbrowser.open(auth_url(), new=2)

    print("Waiting for Spotify authorization...")

    while not hasattr(httpd, 'code'):
        pass  # Wait for code to be set

    code = httpd.code
    httpd.shutdown()
    return code


def get_access_token(code):
    token_url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URL,
        "client_id": conf.client_id,
        "client_secret": conf.client_secret,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(token_url, data=payload, headers=headers)
    response.raise_for_status()
    return response.json()['access_token']


def start_playback(token):
    url = f"https://api.spotify.com/v1/me/player/play"
    headers = {
        'Authorization': "Bearer " + token,
        'Content-Type': "application/json"
    }
    fields = {
        'context_uri': PLAYLIST_URI,
    }

    response = requests.put(url, headers=headers, json=fields)

    if response.status_code != 204:
        print(f"Starting playback failed: {response.reason}")

    url = f"https://api.spotify.com/v1/me/player/shuffle?state=true"
    headers = {
        'Authorization': "Bearer " + token,
    }

    response = requests.put(url, headers=headers)

    if response.status_code not in (200, 204):
        print(f"Enabling shuffle failed: {response.reason}")


def skip(token):
    url = f"https://api.spotify.com/v1/me/player/next"
    headers = {
        'Authorization': "Bearer " + token,
    }
    response = requests.post(url, headers=headers)

    if response.status_code not in (200, 204):
        print(f"Skip failed: {response.reason}")


def enqueue(token, uri):
    url = f"https://api.spotify.com/v1/me/player/queue?uri={uri}"
    headers = {
        'Authorization': "Bearer " + token,
        'Content-Type': "application/json",
    }
    response = requests.post(url, headers=headers)

    if response.status_code not in (200, 204):
        print(f"Enqueue failed: {response.reason}")


def pause(token):
    url = f"https://api.spotify.com/v1/me/player/pause"
    headers = {
        'Authorization': "Bearer " + token
    }
    response = requests.put(url, headers=headers)

    if response.status_code not in (200, 204):
        print(f"Pause failed: {response.reason}")


def resume(token):
    url = f"https://api.spotify.com/v1/me/player/play"
    headers = {
        'Authorization': "Bearer " + token
    }
    response = requests.put(url, headers=headers)

    if response.status_code not in (200, 204):
        print(f"Resume failed: {response.reason}")


def get_current_info(token):
    url = f"https://api.spotify.com/v1/me/player/currently-playing"
    headers = {
        'Authorization': "Bearer " + token
    }
    response = requests.get(url, headers=headers)

    if response.status_code not in (200, 204):
        print(f"Getting track info failed: {response.reason}")

    item = response.json()['item']
    return item['name'], {artist['name'] for artist in item['artists']}, item['uri']


def kill(uri, token):
    assert uri.startswith("spotify:track:")
    track_id = uri[14:]
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    headers = {
        'Authorization': "Bearer " + token
    }
    response = requests.get(url, headers=headers)

    if response.status_code not in (200, 204):
        print(f"Getting track info failed: {response.reason}")

    json = response.json()
    print(f"Name: {json['name']}")
    print(f"Artists: {', '.join(artist['name'] for artist in json['artists'])}")

    answer = input('Confirm removal [y/n] ')
    if answer != 'y':
        print("Removal cancelled")
        return False

    url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}/tracks"
    payload = {
        "tracks": [
            {"uri": uri}
        ]
    }

    headers = {
        "Content-Type": "application/json",
        'Authorization': "Bearer " + token
    }

    response = requests.delete(url, json=payload, headers=headers)

    if response.status_code not in (200, 204):
        print(f"Removing track failed: {response.reason}")
    else:
        print(f"Track successfully removed")
    return True


def uniformize(s):
    t = ''
    for c in s:
        if c in ['(', '-']:
            break
        if c in ['.', '?', '!', '\'', ',', ' ', '´']:
            continue
        t += c

    normalized = unicodedata.normalize('NFD', t)
    without_accents = ''.join(
        ch for ch in normalized
        if unicodedata.category(ch) != 'Mn'
    )
    cleaned = re.sub(r'[^0-9a-zA-Z]', '', without_accents)

    return cleaned.strip().lower()


if __name__ == '__main__':
    token = get_access_token(get_auth_code())
    start_playback(token)

    points = 0
    rounds = 0
    playing = True
    no_skip = False
    failed = []
    try:
        while playing:
            if failed and failed[0][0] <= rounds:
                enqueue(token, failed.pop(0)[1])
            skip(token)
            rounds += 1
            missing_title = True
            artist_guessed = False
            title, artists, uri = get_current_info(token)
            while missing_title or artists or no_skip:
                while not (command := input("Enter Title, Artist or Featuring Artist\n> ")):
                    pass
                if command[0] == '!':
                    match command[1:]:
                        case "skip":
                            print(f'Title: "{title}"')
                            print(f'Missing Artists:', ", ".join(artists))
                            if missing_title and not artist_guessed:
                                failed.append([rounds + 10, uri])
                            break
                        case "kill":
                            if failed and kill(failed[-1][1], token):
                                failed.pop()
                        case "pause":
                            pause(token)
                            input("Press enter to continue...")
                            resume(token)
                        case "quit":
                            playing = False
                            break
                        case "refresh":
                            missing_title = True
                            title, artists, uri = get_current_info(token)
                        case "noskip":
                            no_skip = not no_skip
                        case "again":
                            print(f'Title: "{title}"')
                            print(f'Missing Artists:', ", ".join(artists))
                            failed.append([rounds + 10, uri])
                            break
                else:
                    guess = uniformize(command)
                    if missing_title and guess == uniformize(title):
                        missing_title = False
                        points += 1
                        print("Correct title!")
                    else:
                        for name in artists:
                            if guess == uniformize(name):
                                artist_guessed = True
                                points += 1
                                print("Correct artist!")
                                artists.discard(name)
                                break
                        else:
                            print("No match...")
    finally:
        print(f"You got a total of {points} points over {rounds} rounds.")
