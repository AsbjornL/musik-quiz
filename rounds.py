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


ROUND_LENGTH = 25


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
		print(f"Getting playlist length failed: {response.reason}")

	return response.json()["tracks"]["total"]


def get_playlist(token):
	url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}/tracks"
	headers = {
		'Authorization': "Bearer " + token
	}

	length = get_playlist_length(token)
	if length <= ROUND_LENGTH:
		offset = 0
	else:
		offset = rd.randint(0, length - ROUND_LENGTH - 1)
	
	params = {
		"market": "DK",
		"fields": "items(track(uri))",
		"limit": ROUND_LENGTH,
		"offset": offset,
	}

	response = requests.get(url, headers=headers, params=params)

	if response.status_code != 200:
		print(f"Playing track failed: {response.reason}")

	data = response.json()
	return list(obj['track']['uri'] for obj in data['items'])


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
		for uri in playlist:
			title, artists = get_track_info(uri, token)
			play_track(uri, token)
			title_guessed = False
			artist_guessed = False
			while not title_guessed or artists:
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
						case "kill":
							kill(uri, token)
							playlist.remove(uri)
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
		print(f"{guessed} / {len(playlist)} guessed")
