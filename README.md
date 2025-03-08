# PlexPosterSync

A Python utility to automatically fetch, upload, and manage posters from ThePosterDB for your Plex media library.


## Features

- Seamlessly imports posters from ThePosterDB to your Plex server
- Updates both Movies and TV Shows libraries (including season posters)
- Saves local copies of posters in your media directories
- Optimizes image quality with JPEG compression
- Supports batch processing via import files
- Uses TMDb API for improved media matching (optional)
- Comprehensive logging and error reporting

## Requirements

- Python 3.6+
- Plex Media Server with API access
- ThePosterDB.com access
- Python packages: requests, plexapi, beautifulsoup4, pillow, python-dotenv

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/nichtlegacy/PlexPosterSync.git
   cd PlexPosterSync
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` or use the `.env.example` file with your configuration:
   ```
   PLEX_BASE_URL=http://your-plex-server:32400
   PLEX_TOKEN=your_plex_token_here
   MOVIES_POSTER_DIR=/absolute/path/to/your/movies/posters
   SERIES_POSTER_DIR=/absolute/path/to/your/series/posters
   MOVIES_LIBRARY=Movies
   SERIES_LIBRARY=TV Shows
   JPEG_QUALITY=85
   USE_TMDB=True
   TMDB_API_KEY=your_tmdb_api_key_here
   ```

## Usage

Run the script and follow the interactive prompts:

```bash
python plex_poster_sync.py
```

The script offers two modes:
1. Process a single ThePosterDB URL (set or individual poster)
2. Process multiple URLs from an import file

### Import File Format

Create a text file with ThePosterDB URLs, one per line:
```
https://theposterdb.com/set/12345
https://theposterdb.com/poster/67890
# Lines starting with # are ignored
```

## How It Works

1. Connects to your Plex server using the provided credentials
2. Scrapes poster information from ThePosterDB
3. Finds matching media items in your Plex libraries
4. Downloads, optimizes, and uploads posters to Plex
5. Saves a local copy in your media directories
6. Provides detailed logs of the process

## License

[MIT](LICENSE)

## Acknowledgements

- [ThePosterDB](https://theposterdb.com) for providing high-quality media posters
- [PlexAPI](https://github.com/pkkid/python-plexapi) for Plex server interaction
