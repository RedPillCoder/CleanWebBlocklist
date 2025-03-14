import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib.parse import urlparse
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
import warnings
import re

# Suppress InsecureRequestWarning
warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Custom exceptions
class WebsiteCheckError(Exception):
    pass

class NetworkError(WebsiteCheckError):
    pass

class InvalidWebsiteError(WebsiteCheckError):
    pass

def create_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def contains_required_content(text):
    keywords = [
        "Porn", "Sex", "Adult film", "Adult video", "XXX", "Erotic", "Nude", "Naked", "Hentai", "Milf",
        "Lesbian", "Anal", "Big Ass", "Big Tits", "Asian", "Latina", "Ebony", "Mature", "Threesome",
        "Creampie", "Cosplay", "Transgender", "Animation/Anime", "3D videos", "Step Mom", "Step Dad",
        "Teacher/Student", "Real Amateur", "Gangbangs", "BBW", "BDSM", "Bondage", "Discipline",
        "Sadism", "Masochism", "Fetish", "feet", "latex", "JOI", "Jerk Off Instruction", "Pegging",
        "Facesitting", "Futanari", "Blow Job"
    ]
    pattern = r'\b(?:' + '|'.join(re.escape(keyword) for keyword in keywords) + r')\b'
    return bool(re.search(pattern, text, re.IGNORECASE))

def is_valid_url(url, session):
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = 'http://' + url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            ip = socket.gethostbyname(parsed.netloc)
            logging.info(f"Resolved {parsed.netloc} to {ip}")
        except socket.gaierror:
            raise InvalidWebsiteError(f"Failed to resolve {parsed.netloc}")
        
        response = session.get(url, timeout=15, allow_redirects=True, headers=headers, verify=False)
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('text/html'):
                raise InvalidWebsiteError(f"Invalid content type: {content_type}")
            
            error_texts = [
                "hmm. we're having trouble finding that site",
                "404 not found",
                "403 forbidden",
                "site not found",
                "page not found",
                "this site can't be reached",
                "server not found"
            ]
            if any(error_text in response.text.lower() for error_text in error_texts):
                raise InvalidWebsiteError("Error message found in response content")
            
            if not contains_required_content(response.text):
                raise InvalidWebsiteError("Required content not found")
            
            return True
        else:
            raise InvalidWebsiteError(f"HTTP status code: {response.status_code}")
    except requests.RequestException as e:
        raise NetworkError(f"Network error: {str(e)}")

def check_url(url, session, valid_file):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if is_valid_url(url, session):
                with open(valid_file, 'a') as outfile:
                    outfile.write(f"{url}\n")
                logging.info(f"Valid website: {url}")
                return url, "Valid"
        except NetworkError as e:
            if attempt == max_retries - 1:
                return url, f"Network Issue: {str(e)}"
            time.sleep(1 * (attempt + 1))
        except InvalidWebsiteError as e:
            return url, f"Invalid: {str(e)}"
    return url, "Max retries exceeded"

def main():
    input_file = r"C:\Users\WDAGUtilityAccount\Documents\WebsiteValidator\Websites\websites.txt"
    valid_file = r"C:\Users\WDAGUtilityAccount\Documents\WebsiteValidator\Valid_Websites\valid_websites.txt"
    invalid_file = r"C:\Users\WDAGUtilityAccount\Documents\WebsiteValidator\Invalid_Websites\invalid_websites.txt"
    network_issue_file = r"C:\Users\WDAGUtilityAccount\Documents\WebsiteValidator\Network_Issues\network_issues.txt"

    # Ensure input file exists
    if not os.path.exists(input_file):
        logging.error(f"Input file not found: {input_file}")
        return

    # Clear the output files before starting
    open(valid_file, 'w').close()
    open(invalid_file, 'w').close()
    open(network_issue_file, 'w').close()

    with open(input_file, 'r') as infile:
        urls = [line.strip() for line in infile]

    session = create_session()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(check_url, url, session, valid_file): url for url in urls}
        for future in as_completed(future_to_url):
            url, status = future.result()
            if status.startswith("Invalid"):
                with open(invalid_file, 'a') as outfile:
                    outfile.write(f"{url} - {status}\n")
                logging.info(f"Invalid website: {url} - {status}")
            elif status != "Valid":
                with open(network_issue_file, 'a') as outfile:
                    outfile.write(f"{url} - {status}\n")
                logging.info(f"Network issue: {url} - {status}")
            time.sleep(0.5)  # Rate limiting

    logging.info("Process completed.")
    logging.info(f"Valid websites saved to: {valid_file}")
    logging.info(f"Invalid websites saved to: {invalid_file}")
    logging.info(f"Websites with network issues saved to: {network_issue_file}")

if __name__ == "__main__":
    main()
