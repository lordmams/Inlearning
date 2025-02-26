import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os

BASE_URL = "https://www.w3schools.com/"

def get_next_page(current_url, soup):
    """Find the 'Next' button and extract the next page URL."""
    next_link = soup.find('a', string="Next ❯")
    if next_link and 'href' in next_link.attrs:
        return urljoin(current_url, next_link['href'])
    return None

def extract_main_content(soup, page_url):
    """Extract content from the main section."""
    main_div = soup.find('div', {'class': 'w3-col l10 m12', 'id': 'main'})
    if not main_div:
        return {}

    # Extract title (h1)
    title = main_div.find('h1')
    title_text = title.get_text(strip=True) if title else "No Title"

    # Extract paragraphs
    paragraphs = [p.get_text(strip=True) for p in main_div.find_all('p')]

    # Extract lists (ul and ol)
    lists = []
    for ul in main_div.find_all(['ul', 'ol']):
        items = [li.get_text(strip=True) for li in ul.find_all('li')]
        lists.append(items)

    # Extract code examples
    examples = []
    for code_div in main_div.find_all('div', {'class': 'w3-code'}):
        examples.append(code_div.get_text(strip=True))

    # Extract description if available
    description_div = main_div.find('div', {'class': 'w3-info'})
    description = description_div.get_text(strip=True) if description_div else ""

    # Extract YouTube video link
    video_link = None
    video_anchor = main_div.find('a', {'class': 'ga-featured ga-youtube'})
    if video_anchor and 'href' in video_anchor.attrs:
        video_link = video_anchor['href']

    return {
        "titre": title_text,
        "description": description,  # Include description if found
        "lien": page_url,  # Page URL
        "contenus": {
            "paragraphs": paragraphs,
            "lists": lists,
            "examples": examples
        },
        "categories": "",  # Placeholder for categories
        "niveau": "",  # Placeholder for level
        "durée": ""  # Placeholder for duration
    }

def analyze_page_content(url):
    """Analyze the content of a single page."""
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract main content
    content = extract_main_content(soup, url)

    # Find next page
    next_url = get_next_page(url, soup)

    # Build structured data
    content_data = {
        "url": url,
        "cours": content
    }
    return content_data, next_url

def scrape_course(course):
    """Scrape a course by navigating through its pages."""
    start_url = f"{BASE_URL}{course}/default.asp"
    url = start_url
    all_content = []
    visited_urls = set()  # Track visited URLs

    while url:
        if url in visited_urls:
            print(f"URL already visited: {url}. Ending scrape.")
            break

        print(f"Analyzing: {url}")
        visited_urls.add(url)  # Mark the URL as visited

        try:
            page_content, next_url = analyze_page_content(url)
            all_content.append(page_content)
            url = next_url  # Move to the next page
        except Exception as e:
            print(f"Error analyzing {url}: {e}")
            break

    return all_content

def scrape_courses_from_list(course_list):
    """Scrape multiple courses from a list."""
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)  # Ensure the output directory exists

    for course in course_list:
        print(f"Starting scrape for the {course} course...")
        course_content = scrape_course(course)

        # Save all data to a JSON file in the output directory
        output_file = os.path.join(output_dir, f"{course}_course_content.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(course_content, f, ensure_ascii=False, indent=4)

        print(f"Scraping complete for {course}. Data saved to {output_file}.")

def main():
    # List of courses to scrape
    course_list = ["html", "css", "js","sql","python",'java','php','cpp','cs','react','mysql','jquery','nodejs','git','numpy']  # Example list of courses
    scrape_courses_from_list(course_list)

if __name__ == "__main__":
    main()
