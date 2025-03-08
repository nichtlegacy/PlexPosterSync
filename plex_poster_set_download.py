import requests
import os
import shutil
import sys
from plexapi.server import PlexServer
from bs4 import BeautifulSoup
import time
import re
from PIL import Image
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Global variables from .env
PLEX_BASE_URL = os.getenv("PLEX_BASE_URL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
MOVIES_POSTER_DIR = os.getenv("MOVIES_POSTER_DIR")
SERIES_POSTER_DIR = os.getenv("SERIES_POSTER_DIR")
MOVIES_LIBRARY = os.getenv("MOVIES_LIBRARY", "Movies")  # Default: "Movies"
SERIES_LIBRARY = os.getenv("SERIES_LIBRARY", "TV Shows")  # Default: "TV Shows"
JPEG_QUALITY = os.getenv("JPEG_QUALITY", "85")  # Default: 85, as string, validated later
TMDB_API_KEY = os.getenv("TMDB_API_KEY")  # Optional: TMDb API key
USE_TMDB = os.getenv("USE_TMDB", "True").lower() in ("true", "1", "yes")  # Default: True

# HTTP headers for web requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': 'Windows'
}

def check_env_vars():
    """
    Validates environment variables from .env file.
    Ensures required variables are set and reasonable, logs optional ones.
    Exits the script if critical errors are found.
    """
    errors = []
    print(f"[{datetime.now()}] Checking environment variables...")

    # Check PLEX_BASE_URL
    if not PLEX_BASE_URL:
        errors.append("PLEX_BASE_URL is not specified")
    elif not PLEX_BASE_URL.startswith("http://") and not PLEX_BASE_URL.startswith("https://"):
        errors.append("PLEX_BASE_URL must start with 'http://' or 'https://'")

    # Check PLEX_TOKEN
    if not PLEX_TOKEN:
        errors.append("PLEX_TOKEN is not specified")
    elif len(PLEX_TOKEN) < 10:  # Basic length check for Plex token
        errors.append("PLEX_TOKEN seems invalid (too short)")

    # Check MOVIES_POSTER_DIR
    if not MOVIES_POSTER_DIR:
        errors.append("MOVIES_POSTER_DIR is not specified")
    elif not os.path.isabs(MOVIES_POSTER_DIR):
        errors.append("MOVIES_POSTER_DIR must be an absolute path")

    # Check SERIES_POSTER_DIR
    if not SERIES_POSTER_DIR:
        errors.append("SERIES_POSTER_DIR is not specified")
    elif not os.path.isabs(SERIES_POSTER_DIR):
        errors.append("SERIES_POSTER_DIR must be an absolute path")

    # Check MOVIES_LIBRARY
    if not MOVIES_LIBRARY:
        errors.append("MOVIES_LIBRARY is not specified (default 'Movies' overridden with empty value)")

    # Check SERIES_LIBRARY
    if not SERIES_LIBRARY:
        errors.append("SERIES_LIBRARY is not specified (default 'TV Shows' overridden with empty value)")

    # Check JPEG_QUALITY
    try:
        quality = int(JPEG_QUALITY)
        if not 1 <= quality <= 100:
            errors.append("JPEG_QUALITY must be between 1 and 100")
    except ValueError:
        errors.append("JPEG_QUALITY must be a number")

    # Optional variables (info only)
    if not TMDB_API_KEY:
        print(f"[{datetime.now()}] Info: TMDB_API_KEY not specified, TMDb fallback will be disabled")
    elif len(TMDB_API_KEY) < 10:
        print(f"[{datetime.now()}] Warning: TMDB_API_KEY seems invalid (too short), TMDb fallback may fail")
    
    print(f"[{datetime.now()}] Info: USE_TMDB is {'enabled' if USE_TMDB else 'disabled'}")

    if errors:
        print(f"[{datetime.now()}] Errors found in .env configuration:")
        for error in errors:
            print(f"[{datetime.now()}] - {error}")
        print(f"[{datetime.now()}] Exiting script.")
        sys.exit(1)
    print(f"[{datetime.now()}] All required environment variables are valid")

def clean_filename(filename):
    """Removes invalid characters from filenames."""
    invalid_chars = r'[:*?"<>|\/]'
    return re.sub(invalid_chars, '', filename)

def plex_setup():
    """Sets up the Plex server connection using PLEX_BASE_URL and PLEX_TOKEN."""
    print(f"[{datetime.now()}] Connecting to Plex server: {PLEX_BASE_URL}")
    try:
        plex = PlexServer(PLEX_BASE_URL, PLEX_TOKEN)
        print(f"[{datetime.now()}] Successfully connected to Plex")
        return plex
    except Exception as e:
        print(f"[{datetime.now()}] Failed to connect to Plex server: {e}")
        return None

def fetch_page(url, retries=3, delay=5, timeout=30):
    """Fetches a webpage with retries and returns its BeautifulSoup object."""
    print(f"[{datetime.now()}] Fetching page: {url}")
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            if response.status_code == 200:
                print(f"[{datetime.now()}] Page loaded successfully (Status: {response.status_code})")
                return BeautifulSoup(response.text, 'html.parser')
            print(f"[{datetime.now()}] Failed to load page, Status: {response.status_code}")
            time.sleep(delay)
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now()}] Error fetching page {url}: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    print(f"[{datetime.now()}] Failed to load page after {retries} attempts")
    return None

def compress_image(input_path, output_path, quality=int(JPEG_QUALITY)):
    """Compresses an image to JPEG format with specified quality."""
    print(f"[{datetime.now()}] Compressing image: {input_path}")
    try:
        with Image.open(input_path) as img:
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            if 'xmp' in img.info:
                del img.info['xmp']
            img.save(output_path, "JPEG", quality=quality, optimize=True)
        print(f"[{datetime.now()}] Image successfully compressed to: {output_path} (Quality: {quality}%)")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] Error compressing image: {e}")
        return False

def scrape_posterdb(url):
    """Scrapes a ThePosterDB set URL for movie and TV show posters."""
    print(f"[{datetime.now()}] Scraping poster set from: {url}")
    soup = fetch_page(url)
    if not soup:
        print(f"[{datetime.now()}] No data retrieved from page")
        return [], []
    
    movieposters = []
    showposters = []
    
    poster_div = soup.find('div', class_='row d-flex flex-wrap m-0 w-100 mx-n1 mt-n1')
    if not poster_div:
        print(f"[{datetime.now()}] No poster grid found on page")
        return [], []

    posters = poster_div.find_all('div', class_='col-6 col-lg-2 p-1')
    print(f"[{datetime.now()}] Found posters: {len(posters)}")
    for poster in posters:
        media_type = poster.find('a', class_="text-white", attrs={'data-toggle': 'tooltip'})['title']
        overlay_div = poster.find('div', class_='overlay')
        poster_id = overlay_div.get('data-poster-id')
        poster_url = f"https://theposterdb.com/api/assets/{poster_id}"
        title_p = poster.find('p', class_='p-0 mb-1 text-break').string
        print(f"[{datetime.now()}] Processing poster - Type: {media_type}, Title: {title_p}")

        if media_type == "Movie":
            title_split = title_p.split(" (")
            title = title_split[0]
            year = int(title_split[-1].split(")")[0])
            movieposters.append({"title": title, "year": year, "url": poster_url, "source": "posterdb"})
            print(f"[{datetime.now()}] Movie detected: {title} ({year})")
        elif media_type == "Show":
            title = title_p.split(" (")[0]
            try:
                year = int(title_p.split(" (")[1].split(")")[0])
            except (IndexError, ValueError):
                year = None
            season = "Cover" if " - " not in title_p else title_p.split(" - ")[-1]
            if season == "Specials":
                season = 0
            elif "Season" in season:
                season = int(season.split(" ")[1])
            showposters.append({
                "title": title,
                "url": poster_url,
                "season": season,
                "episode": None,
                "year": year,
                "source": "posterdb"
            })
            print(f"[{datetime.now()}] Show detected: {title} ({year}), Season: {season}")
    return movieposters, showposters

def scrape_single_poster(url):
    """Scrapes a single ThePosterDB poster URL."""
    print(f"[{datetime.now()}] Scraping single poster from: {url}")
    soup = fetch_page(url)
    poster_id = url.split('/')[-1]
    poster_url = f"https://theposterdb.com/api/assets/{poster_id}"

    if not soup:
        print(f"[{datetime.now()}] Page could not be loaded, using fallback URL")
        return [{"title": None, "year": None, "url": poster_url, "source": "posterdb"}], []

    type_elem = next((p for p in soup.find_all('p', class_='pb-0 mb-0') 
                     if p.find('strong') and p.find('strong').text == "Type:"), None)
    media_type = type_elem.text.split("Type:")[1].strip() if type_elem else "Movie"
    print(f"[{datetime.now()}] Detected media type: {media_type}")

    title_elem = soup.find('p', class_='h1 m-0 mt-2 text-center text-md-left text-wrap')
    title_text = title_elem.find('a').text.strip() if title_elem else soup.find('title').text.strip()
    print(f"[{datetime.now()}] Extracted title: {title_text}")

    title_match = re.match(r"(.+?)\s*\((\d{4})\)", title_text)
    if not title_match:
        print(f"[{datetime.now()}] Could not parse title/year, using fallback")
        return [{"title": None, "year": None, "url": poster_url, "source": "posterdb"}], []

    title, year = title_match.group(1).strip(), int(title_match.group(2))
    print(f"[{datetime.now()}] Parsed: Title: {title}, Year: {year}")
    
    if media_type == "Movie":
        print(f"[{datetime.now()}] Single movie detected: {title} ({year})")
        return [{"title": title, "year": year, "url": poster_url, "source": "posterdb"}], []
    
    season = "Cover"
    if " - " in title_text:
        split_season = title_text.split(" - ")[-1]
        season = 0 if split_season == "Specials" else (
            int(split_season.split(" ")[1]) if "Season" in split_season else "Cover")
    print(f"[{datetime.now()}] Single show detected: {title} ({year}), Season: {season}")
    
    return [], [{
        "title": title,
        "url": poster_url,
        "season": season,
        "episode": None,
        "year": year,
        "source": "posterdb"
    }]

def download_poster(url, temp_path, retries=3, delay=2):
    """Downloads a poster image with retries."""
    print(f"[{datetime.now()}] Downloading poster from: {url}")
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                print(f"[{datetime.now()}] Poster successfully downloaded to: {temp_path}")
                return True
            print(f"[{datetime.now()}] Download failed, Status: {response.status_code}")
            time.sleep(delay)
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now()}] Error downloading from {url}: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    print(f"[{datetime.now()}] Download failed after {retries} attempts")
    return False

def get_alternative_titles(title, year, item_type="movie"):
    """
    Retrieves alternative titles from TMDb as a fallback.
    Returns original title if TMDb is disabled or API key is missing.
    """
    if not USE_TMDB:
        print(f"[{datetime.now()}] TMDb is disabled (USE_TMDB=False), skipping fallback")
        return [title]
    if not TMDB_API_KEY:
        print(f"[{datetime.now()}] TMDb API key missing, skipping fallback")
        return [title]
    alt_titles = set([title])
    tmdb_url = "https://api.themoviedb.org/3/search/movie" if item_type == "movie" else "https://api.themoviedb.org/3/search/tv"
    params = {"api_key": TMDB_API_KEY, "query": title}
    try:
        response = requests.get(tmdb_url, params=params, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        if "results" not in data or not data["results"]:
            print(f"[{datetime.now()}] No TMDb results for {title}")
            return list(alt_titles)
        for result in data["results"][:5]:
            release_year = (
                result.get("release_date", "").split("-")[0] if item_type == "movie" else
                result.get("first_air_date", "").split("-")[0]
            )
            if release_year == str(year):
                alt_titles.add(result.get("title") or result.get("name"))
                alt_titles.add(result.get("original_title") or result.get("original_name"))
                details_url = (
                    f"https://api.themoviedb.org/3/movie/{result['id']}/alternative_titles" if item_type == "movie" else
                    f"https://api.themoviedb.org/3/tv/{result['id']}/alternative_titles"
                )
                details_response = requests.get(details_url, params={"api_key": TMDB_API_KEY}, headers=HEADERS)
                details_response.raise_for_status()
                details_data = details_response.json()
                for alt in details_data.get("titles", []):
                    alt_titles.add(alt["title"])
                break
        print(f"[{datetime.now()}] Alternative titles for {title} ({year}): {alt_titles}")
        return list(alt_titles)
    except Exception as e:
        print(f"[{datetime.now()}] Error querying TMDb for {title} ({year}): {e}")
        return list(alt_titles)

def find_plex_item(section, title, year, item_type="movie"):
    """Searches for an item in Plex, with optional TMDb fallback for alternative titles."""
    print(f"[{datetime.now()}] Searching in Plex: {title} ({year})")
    results = section.search(title=title, year=year)
    if results:
        print(f"[{datetime.now()}] Direct Plex match for {title} ({year}): {results[0].title}")
        return results[0]
    results = section.search(title=title)
    if results:
        print(f"[{datetime.now()}] Plex match without year for {title}: {results[0].title} (Year in Plex: {results[0].year})")
        return results[0]
    if USE_TMDB and TMDB_API_KEY:
        print(f"[{datetime.now()}] Falling back to TMDb for {title} ({year})")
        alt_titles = get_alternative_titles(title, year, item_type)
        for alt_title in alt_titles:
            if alt_title != title:
                results = section.search(title=alt_title)
                if results:
                    print(f"[{datetime.now()}] Plex match via TMDb title: {alt_title} for {title} ({year})")
                    return results[0]
    else:
        print(f"[{datetime.now()}] TMDb fallback disabled or no API key provided")
    print(f"[{datetime.now()}] No match for {title} ({year}) in {item_type} after Plex search")
    return None

def update_series(plex, posters, stats):
    """Updates TV show posters in Plex and moves them to the specified directory."""
    series_section = plex.library.section(SERIES_LIBRARY)
    temp_raw_path = "temp_poster_raw.jpg"
    temp_compressed_path = "temp_poster_compressed.jpg"
    processed_series = set()

    print(f"[{datetime.now()}] Processing {len(posters)} TV show posters in library: {SERIES_LIBRARY}")
    for poster in posters:
        matched_show = find_plex_item(series_section, poster["title"], poster["year"], "show")
        if not matched_show:
            print(f"[{datetime.now()}] No match found in Plex")
            stats["skipped"] += 1
            continue

        show_key = f"{matched_show.title} ({matched_show.year})"
        if show_key in processed_series and poster["season"] == "Cover":
            print(f"[{datetime.now()}] Skipping already processed show: {show_key}")
            stats["skipped"] += 1
            continue

        print(f"[{datetime.now()}] Found Plex show: {show_key}, Season: {poster['season']}")
        if download_poster(poster["url"], temp_raw_path):
            poster_path = temp_compressed_path if compress_image(temp_raw_path, temp_compressed_path) else temp_raw_path
            
            try:
                upload_target = (matched_show if poster["season"] == "Cover" else 
                               matched_show.season("Specials") if poster["season"] == 0 else 
                               matched_show.season(poster["season"]))
                print(f"[{datetime.now()}] Uploading poster for: {upload_target.title} - Season {poster['season']}")
                upload_target.uploadPoster(filepath=poster_path)
                time.sleep(6)  # Delay to avoid overwhelming Plex server
                print(f"[{datetime.now()}] Poster successfully uploaded")
            except Exception as e:
                print(f"[{datetime.now()}] Error uploading poster: {e}")
                stats["failed"] += 1
                stats["errors"].append(f"{matched_show.title} - Season {poster['season']}: {e}")
                continue

            target_dir = os.path.join(SERIES_POSTER_DIR, os.path.basename(
                os.path.normpath(matched_show.locations[0]) if matched_show.locations else 
                clean_filename(f"{matched_show.title} ({matched_show.year})")))
            target_filename = ("poster.jpg" if poster["season"] == "Cover" else 
                             f"Season{poster['season']:02d}.jpg" if isinstance(poster["season"], int) else "poster.jpg")
            target_path = os.path.join(target_dir, target_filename)
            print(f"[{datetime.now()}] Target path for poster: {target_path}")
            
            os.makedirs(target_dir, exist_ok=True)
            try:
                shutil.move(poster_path, target_path)
                print(f"[{datetime.now()}] Poster moved to: {target_path}")
                stats["success"] += 1
                processed_series.add(show_key)
                print(f"[{datetime.now()}] {'-' * 50}")
            except Exception as e:
                print(f"[{datetime.now()}] Error moving poster to {target_path}: {e}")
                stats["failed"] += 1
                stats["errors"].append(f"Move failed for {target_path}: {e}")
            finally:
                for temp in [temp_raw_path, temp_compressed_path]:
                    if os.path.exists(temp):
                        os.remove(temp)
        else:
            print(f"[{datetime.now()}] Skipping update due to download failure")
            stats["failed"] += 1

def update_movies(plex, posters, stats):
    """Updates movie posters in Plex and moves them to the specified directory."""
    movies_section = plex.library.section(MOVIES_LIBRARY)
    temp_raw_path = "temp_poster_raw.jpg"
    temp_compressed_path = "temp_poster_compressed.jpg"
    processed_movies = set()

    print(f"[{datetime.now()}] Processing {len(posters)} movie posters in library: {MOVIES_LIBRARY}")
    for poster in posters:
        matched_movie = find_plex_item(movies_section, poster["title"], poster["year"], "movie")
        if not matched_movie:
            print(f"[{datetime.now()}] No match found in Plex")
            stats["skipped"] += 1
            continue

        movie_key = f"{matched_movie.title} ({matched_movie.year})"
        if movie_key in processed_movies:
            print(f"[{datetime.now()}] Skipping already processed movie: {movie_key}")
            stats["skipped"] += 1
            continue

        print(f"[{datetime.now()}] Found Plex movie: {movie_key}")
        if download_poster(poster["url"], temp_raw_path):
            poster_path = temp_compressed_path if compress_image(temp_raw_path, temp_compressed_path) else temp_raw_path
            
            try:
                print(f"[{datetime.now()}] Uploading poster for: {movie_key}")
                matched_movie.uploadPoster(filepath=poster_path)
                time.sleep(6)  # Delay to avoid overwhelming Plex server
                print(f"[{datetime.now()}] Poster successfully uploaded")
            except Exception as e:
                print(f"[{datetime.now()}] Error uploading poster: {e}")
                stats["failed"] += 1
                stats["errors"].append(f"{movie_key}: Upload failed - {e}")
                continue

            target_dir = os.path.join(MOVIES_POSTER_DIR, os.path.basename(
                os.path.dirname(matched_movie.locations[0]) if matched_movie.locations else 
                clean_filename(f"{matched_movie.title} ({matched_movie.year})")))
            target_path = os.path.join(target_dir, "poster.jpg")
            print(f"[{datetime.now()}] Target path for poster: {target_path}")
            
            os.makedirs(target_dir, exist_ok=True)
            try:
                shutil.move(poster_path, target_path)
                print(f"[{datetime.now()}] Poster moved to: {target_path}")
                stats["success"] += 1
                processed_movies.add(movie_key)
                print(f"[{datetime.now()}] {'-' * 50}")
            except Exception as e:
                print(f"[{datetime.now()}] Error moving poster to {target_path}: {e}")
                stats["failed"] += 1
                stats["errors"].append(f"Move failed for {target_path}: {e}")
            finally:
                for temp in [temp_raw_path, temp_compressed_path]:
                    if os.path.exists(temp):
                        os.remove(temp)
        else:
            print(f"[{datetime.now()}] Skipping update due to download failure")
            stats["failed"] += 1

def read_import_file(file_path):
    """Reads a file containing ThePosterDB URLs, ignoring comments and empty lines."""
    print(f"[{datetime.now()}] Reading import file: {file_path}")
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            urls = [line.strip() for line in file if line.strip() and not line.startswith('#') and 'theposterdb.com' in line]
        print(f"[{datetime.now()}] Found URLs: {len(urls)}")
        return urls
    except Exception as e:
        print(f"[{datetime.now()}] Error reading import file: {e}")
        return []

def main():
    """Main function to orchestrate poster scraping and updating."""
    # Validate environment variables first
    check_env_vars()

    plex = plex_setup()
    if not plex:
        return

    stats = {"success": 0, "failed": 0, "skipped": 0, "errors": []}
    
    mode = input("Single URL (1) or Import File (2)? [1/2]: ").strip()
    
    if mode == "1":
        url = input("Enter ThePosterDB URL: ").strip()
        if not url or 'theposterdb.com' not in url:
            print(f"[{datetime.now()}] Invalid URL")
            return
        
        print(f"[{datetime.now()}] Processing single URL: {url}")
        movieposters, showposters = (scrape_single_poster(url) if "/poster/" in url else scrape_posterdb(url))
        print(f"[{datetime.now()}] Found movies: {len(movieposters)}, shows: {len(showposters)}")
        if movieposters:
            update_movies(plex, movieposters, stats)
        if showposters:
            update_series(plex, showposters, stats)

    elif mode == "2":
        import_file = input("Enter path to import file: ").strip()
        if not os.path.exists(import_file):
            print(f"[{datetime.now()}] File not found")
            return
        
        urls = read_import_file(import_file)
        for url in urls:
            print(f"[{datetime.now()}] Processing URL from file: {url}")
            movieposters, showposters = (scrape_single_poster(url) if "/poster/" in url else scrape_posterdb(url))
            print(f"[{datetime.now()}] Found movies: {len(movieposters)}, shows: {len(showposters)}")
            if movieposters:
                update_movies(plex, movieposters, stats)
            if showposters:
                update_series(plex, showposters, stats)
            time.sleep(2)  # Delay between processing URLs to avoid overwhelming services

    else:
        print(f"[{datetime.now()}] Invalid selection")
        return

    print(f"\n[{datetime.now()}] Summary:")
    print(f"[{datetime.now()}] Successful: {stats['success']}")
    print(f"[{datetime.now()}] Failed: {stats['failed']}")
    print(f"[{datetime.now()}] Skipped: {stats['skipped']}")
    if stats["errors"]:
        print(f"[{datetime.now()}] Error details:")
        for error in stats["errors"]:
            print(f"[{datetime.now()}] - {error}")

if __name__ == "__main__":
    main()