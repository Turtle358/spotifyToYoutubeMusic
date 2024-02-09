import os
import spotipy
import pickle
from spotipy import SpotifyOAuth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
SCOPES = ['https://www.googleapis.com/auth/youtube']


def getKeys():
    if os.path.exists('Spotify.keys'):
        with open('Spotify.keys','rb') as f:
            keys = pickle.load(f)
    else:
        keys = {'spotify_id': input('Please enter your spotify id: '),
                'spotify_secret': input('Please enter your spotify secret: ')}
        with open('Spotify.keys','rb') as f:
            pickle.dump(keys, f)
    return keys


def getSpotifySongs():
    keys = getKeys()
    # Authenticating with spotify
    authManager = SpotifyOAuth(client_id=keys['spotify_id'], client_secret=keys['spotify_secret'],
                                redirect_uri='http://google.com/callback',
                                scope='user-library-read,user-read-playback-state,user-modify-playback-state,\
                                streaming,user-read-currently-playing,playlist-read-private,playlist-read-collaborative,\
                                user-follow-read,user-top-read')

    sp = spotipy.Spotify(auth_manager=authManager)
    totalTracks = round(int(sp.current_user_saved_tracks()['total'])/50)
    totalSongs = []
    j = 0
    for i in range(totalTracks):
        results = sp.current_user_saved_tracks(offset=j, limit=50)
        j+=50
        songNames = [song['track']['name'] for song in results['items']]
        artistNames = [song['track']['artists'][0]['name'] for song in results['items']]
        for i, song in enumerate(songNames):
            totalSongs.append([song, artistNames[i]])
    return totalSongs


def authoriseAPI():
    creds = None
    try:
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    except Exception as e:
        print(f'Exception: {e}')

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json',
                scopes=SCOPES,
                redirect_uri='http://localhost:8000',
            )

            creds = flow.run_local_server(port=8000)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds


def searchSong(service, songName, artistName):
    request = service.search().list(
        q=f'{songName} {artistName}',
        part='id',
        maxResults=1,
        type='video',
        videoCategoryId='10'
    )

    response = request.execute()

    if 'items' in response:
        for item in response['items']:
            if item['id']['kind'] == 'youtube#video':
                return item['id']['videoId']

    return None


def batchRequestCallback(requestID, response, exception):
    if exception is not None:
        print('Error occurred', exception)
    else:
        print('Song added to playlist successfully')


def createPlaylist(songs):
    creds = authoriseAPI()
    service = build('youtube', 'v3', credentials=creds)

    playlistResponse = service.playlists().insert(
        part='snippet',
        body={
            'snippet': {
                'title': 'Your Liked Playlist',
                'description': 'your liked playlist',
                'privacyStatus': 'private'
            }
        }
    ).execute()

    playlistID = playlistResponse['id']

    batchRequestItems =[]

    for song in songs:
        songName, artistName = song
        videoID = searchSong(service, songName, artistName)
        if videoID:
            batchRequestItems.append({
                'snippet': {
                    'playlistId': playlistID,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': videoID
                    }
                }
            })
            print(f"Added {songName} by {artistName} to the playlist.")
        else:
            print(f"Could not find {songName} by {artistName} on YouTube Music.")

    batchRequest = service.new_batch_http_request(callback=batchRequestCallback)
    for i, item in enumerate(batchRequestItems):
        batchRequest.add(service.playlistItems().insert(
            part='snippet',
            body=item
        ))
        batchRequest.execute()

    print("Playlist created and songs added successfully!")


if __name__ == '__main__':
    songs = getSpotifySongs()
    createPlaylist(songs)
