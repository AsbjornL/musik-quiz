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
HARD_MODE = False


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
	return json['name'], [artist['name'] for artist in json['artists']]


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
		tracks.append((track['uri'], track['name'], [artist['name'] for artist in track['artists']]))
	print(f"Retrieved {num} tracks")
	return tracks


if __name__ == '__main__':
	token = get_access_token(get_auth_code())
	rd.seed(time.time())
	playlist = get_playlist(token)
	all_guessed = False
	start_time = time.time()
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
			artists = [artist for artist in const_artists]
			i += 1
			play_track(uri, token)
			title_guessed = False
			artist_guessed = False
			keep_playing = False
			title_hint = 0
			artist_hint = 0
			hint_used = False
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
								remaining.pop()
								break
						case "quit":
							exit()
						case "standing":
							print(f"{i} / {len(playlist)}")
						case "hint":
							hint_used = True
							if not title_guessed and title_hint < len(title):
								title_hint += 1
								print(f"Title: {title[:title_hint]}")
							elif artists and artist_hint < len(artists[0]):
								artist_hint += 1
								print(f"Artist: {artists[0][:artist_hint]}")
						case "time":
							print(f"Minutes spents: {(time.time() - start_time) // 60}")
				else:
					guess = uniformize(command)
					if not title_guessed and guess == uniformize(title):
						title_guessed = True
						print("Correct title!")
					else:
						for name in artists:
							if guess == uniformize(name):
								print("Correct artist!")
								artists = [artist for artist in artists if artist != name]
								artist_hint = 0
								if HARD_MODE:
									artist_guessed = not artists
								else:
									artist_guessed = True
								break
						else:
							print("No match...")
			print(f'Title: "{title}"')
			print(f'Missing Artists:', ", ".join(artists))
			if hint_used or not artist_guessed or not title_guessed:
				all_guessed = False
			else:
				guessed += 1
				remaining.pop()
		print(f"{guessed} / {len(playlist)} guessed")
		if ELIMINATION:
			playlist = remaining
	time_spent = int(time.time() - start_time)
	print(f"Time Spent: {time_spent // 60}m {time_spent % 60}s")
