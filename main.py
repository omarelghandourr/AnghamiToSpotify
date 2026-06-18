from bs4 import BeautifulSoup
import configparser
import logging
from tqdm import tqdm
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()


# Function to load the details from the configuration file
def load_details():
    config = configparser.ConfigParser()
    config.read('config.ini')
    html_file_path = config.get('Anghami', 'html_file_path')
    client_id = config.get('Spotify', 'client_id')
    client_secret = config.get('Spotify', 'client_secret')
    redirect_url = config.get('Spotify', 'redirect_url')
    username = config.get('Spotify', 'username')
    spotify_playlist_name = config.get('Spotify', 'playlist_name')
    save_to_text = config.getboolean('General', 'save_to_text')
    txt_save_path = config.get('General', 'txt_save_path')
    txt_song_artist_separator = config.get('General', 'txt_song_artist_separator')
    return html_file_path, client_id, client_secret, redirect_url, username, spotify_playlist_name, save_to_text, txt_save_path, txt_song_artist_separator


def read_html_file(html_file_path):
    with open(html_file_path, encoding="utf8") as f:
        content = f.read()
    return content


def extract_songs_and_artists(content):
    soup = BeautifulSoup(content, 'html.parser')
    class_lst = ["cell cell-title", "cell cell-title marquee"]
    song_divs = soup.find_all("div", class_=class_lst)
    artist_divs = soup.find_all("div", {"class": "cell cell-artist"})
    songs = [div.find("span").text for div in song_divs]
    artists = [div.text for div in artist_divs]
    return songs, artists


def save_playlist_to_text(songs, artists, txt_save_path, txt_song_artist_separator):
    with open(txt_save_path, 'w', encoding="utf8") as fp:
        for song, artist in zip(songs, artists):
            fp.write(f"{song}{txt_song_artist_separator}{artist}\n")


def authenticate_spotify(client_id, client_secret, redirect_url, username):

    scope = (
        "playlist-modify-public "
        "playlist-modify-private "
        "playlist-read-private "
        "playlist-read-collaborative "
        "user-read-private"
    )

    print("USING SCOPE:")
    print(scope)

    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_url,
            scope=scope,
            open_browser=True
        )
    )

    return sp


def create_spotify_playlist(sp, spotify_playlist_name):
    playlist = sp.current_user_playlist_create(
        name=spotify_playlist_name,
        public=True,
        description="Imported from Anghami"
    )
    return playlist['id']


def search_and_add_tracks(sp, playlist_id, songs, artists, username):
    not_found = []
    for song, artist in tqdm(zip(songs, artists), total=len(songs), bar_format="{l_bar}{bar}{r_bar}", colour='green'):
        try:
            res = sp.search(q=f"{song} {artist}", type='track', limit=1)
            if len(res['tracks']['items']) > 0:
                uri = res['tracks']['items'][0]['uri']
                sp.user_playlist_add_tracks(user=username, playlist_id=playlist_id, tracks=[uri])
            else:
                not_found.append(f"{song} {artist}")
        except spotipy.SpotifyException as e:
            logger.error(f"Spotify Error: {str(e)}")
            not_found.append(f"{song} {artist}")

    return not_found


def main():
    # Load details from configuration file
    html_file_path, client_id, client_secret, redirect_url, username, spotify_playlist_name, save_to_text, txt_save_path, txt_song_artist_separator = load_details()

    # Read the HTML file
    content = read_html_file(html_file_path)

    # Extract songs and artists from the HTML
    songs, artists = extract_songs_and_artists(content)

    # Check if the number of songs matches the number of artists
    if len(songs) != len(artists):
        logger.error("Error: Number of songs and artists do not match.")
        return

    # Print the playlist details
    logger.info("\nPlaylist Details:")
    for song, artist in zip(songs, artists):
        logger.info(f"{song} {txt_song_artist_separator} {artist}")

    # Save the playlist to a text file
    if save_to_text:
        save_playlist_to_text(songs, artists, txt_save_path, txt_song_artist_separator)
        logger.info("Playlist saved to text file.")

    # Authenticate and create a new playlist on Spotify
    sp = authenticate_spotify(client_id, client_secret, redirect_url, username)

    print("\n=== CURRENT USER ===")
    user = sp.current_user()

    print("ID:", user["id"])
    print("Display Name:", user.get("display_name"))
    print("Product:", user.get("product"))

    print("\n=== PLAYLIST ACCESS TEST ===")
    print(sp.current_user_playlists(limit=1))
    playlist_id = create_spotify_playlist(
        sp,
        spotify_playlist_name
    )
    # Search and add tracks to the Spotify playlist
    logger.info("Importing playlist to Spotify...")
    not_found = search_and_add_tracks(sp, playlist_id, songs, artists, username)

    logger.info("Playlist import completed.")

    # Print the not found songs
    if len(not_found) > 0:
        logger.info("\nThe following songs could not be found on Spotify:")
        for song in not_found:
            logger.info(song)


if __name__ == '__main__':
    main()
