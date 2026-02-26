import requests
import random as rd
import time
from main import (
	get_access_token,
	get_auth_code,
	pause,
	resume,
	uniformize,
	kill,
	PLAYLIST_ID,
	PLAYLIST_URI,
)


ROUND_LENGTH = 200
ELIMINATION = True


def get_track_info(uri, token):
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
	return json['name'], set(artist['name'] for artist in json['artists'])


def play_track(uri, token):
	url = f"https://api.spotify.com/v1/me/player/play"
	headers = {
		'Authorization': "Bearer " + token,
		'Content-Type': "application/json"
	}
	fields = {
		'uris': [uri]
	}

	response = requests.put(url, headers=headers, json=fields)

	if response.status_code != 204:
		print(f"Playing track failed: {response.reason}")


def get_playlist_length(token):
	url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}"
	headers = {
		"Authorization": f"Bearer {token}"
	}

	response = requests.get(url, headers=headers, params={"fields": "tracks(total)"})
	if response.status_code != 200:
		print(f"Getting playlist length failed: {response.reason} - {response.text}")

	return response.json()["tracks"]["total"]


def get_playlist(token):
	length = get_playlist_length(token)

	idx = sorted(rd.sample(range(length), k=min(length, ROUND_LENGTH)))

	tracks = []
	cnt = 1
	for i in range(1, len(idx) + 1):
		if i < len(idx) and idx[i] - 1 == idx[i-1]:
			cnt += 1
		else:
			tracks.extend(get_playlist_track(idx[i - cnt], token, num=cnt))
			cnt = 1

	return tracks


def get_playlist_track(i, token, num=1):
	if num > 50:
		return get_playlist_track(i, token, num=50) + get_playlist_track(i + 50, token, num=num - 50)
	url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}/tracks"
	headers = {
		'Authorization': "Bearer " + token
	}

	params = {
		"market": "DK",
		"fields": "items(track(uri,artists(name),name))",
		"limit": num,
		"offset": i,
	}

	response = requests.get(url, headers=headers, params=params)

	if response.status_code != 200:
		print(f"Playing track failed: {response.reason}")

	tracks = []
	data = response.json()
	for blob in data['items']:
		track = blob['track']
		tracks.append((track['uri'], track['name'], {artist['name'] for artist in track['artists']}))
	return tracks


if __name__ == '__main__':
	token = get_access_token(get_auth_code())
	rd.seed(time.time())
	playlist = get_playlist(token)
	all_guessed = False
	while not all_guessed:
		print("New round!")
		guessed = 0
		all_guessed = True
		rd.shuffle(playlist)
		i = 0
		remaining = []
		while i < len(playlist):
			remaining.append(playlist[i])
			uri, title, const_artists = playlist[i]
			artists = {artist for artist in const_artists}
			i += 1
			play_track(uri, token)
			title_guessed = False
			artist_guessed = False
			keep_playing = False
			while keep_playing or not title_guessed or artists:
				while not (command := input("Enter Title, Artist, or a Command\n> ")):
					pass
				if command[0] == '!':
					match command[1:]:
						case "skip":
							break
						case "pause":
							pause(token)
							input("Press enter to continue...")
							resume(token)
						case "replay":
							play_track(uri, token)
						case "play":
							keep_playing = True
						case "kill":
							if kill(uri, token):
								i -= 1
								playlist = [track for track in playlist if track[0] != uri]
								break
						case "quit":
							exit()
				else:
					guess = uniformize(command)
					if not title_guessed and guess == uniformize(title):
						title_guessed = True
						print("Correct title!")
					else:
						for name in artists:
							if guess == uniformize(name):
								artist_guessed = True
								print("Correct artist!")
								artists.discard(name)
								break
						else:
							print("No match...")
			print(f'Title: "{title}"')
			print(f'Missing Artists:', ", ".join(artists))
			if not artist_guessed or not title_guessed:
				all_guessed = False
			else:
				guessed += 1
				remaining.pop()
		print(f"{guessed} / {len(playlist)} guessed")
		if ELIMINATION:
			playlist = remaining
