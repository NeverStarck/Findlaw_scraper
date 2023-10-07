# Fuck cloudflare, all my homies use cloudscraper
import os
import re
import json
import random
import time
import logging
import cloudscraper
from bs4 import BeautifulSoup as bs
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(
    filename='reqs.log',
    level=logging.INFO,  # You can adjust the log level as needed
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
scraper = cloudscraper.CloudScraper()

def create_directory(parent_directory, child_directory=None):
    current_directory = os.getcwd()
    parent_folder = os.path.join(current_directory, "results", parent_directory)

    if not os.path.exists(parent_folder):
        os.makedirs(parent_folder)

    if not child_directory:
        logger.info(f"Directory '{parent_directory}' created successfully.\n")
        return

    custom_directory = os.path.join(parent_folder, child_directory)

    if os.path.exists(custom_directory):
        logger.info(f"The directory '{child_directory}' already exists inside '{parent_directory}'.\n")
    else:
        os.makedirs(custom_directory)
        logger.info(f"Directory '{child_directory}' created successfully inside '{parent_directory}'.\n")

def get_all_states() -> list[str]:
    req = scraper.get(f"https://lawyers.findlaw.com/")
    if req.status_code != 200:
        logger.info(f"Failed to retrieve page: States\n")
        logger.info(f"req: {req}\n")
        return []

    soup = bs(req.text, 'html.parser')

    links_li = soup.find_all('li', class_='map-module__state-list-item')
    return ['-'.join(link.text.lower().split(' ')) for link in links_li]

def get_all_state_cities(state) -> list[str]:
    req = scraper.get(f"https://lawyers.findlaw.com/lawyer/stateallcities/{state}")
    if req.status_code != 200:
        logger.info(f"Failed to retrieve page: State Cities\n")
        logger.info(f"req: {req}\n")
        return []

    soup = bs(req.text, 'html.parser')
    all_cities = []

    links_div = soup.find_all('div', class_='links')
    for div in links_div:
        cities = ['-'.join(link.text.lower().split(' '))for link in div.find_all('a')]
        all_cities.extend(cities)

    return all_cities

def get_all_practices() -> list[str]:
    regex = r'\/firm\/([a-z-]+)\/'

    # All the practices are the same for each state, so we can just use Alabama
    req = scraper.get(f"https://lawyers.findlaw.com/lawyer/statepractice/alabama/abbeville")

    if req.status_code != 200:
        logger.info(f"Failed to retrieve page: Practices\n")
        logger.info(f"req: {req}\n")

        return []

    soup = bs(req.text, 'html.parser')
    all_practices = []

    links_div = soup.find('ul', class_='links')
    for li in links_div:
        for link in li.find_all('a'):
            href = link.get('href')
            match = re.search(regex, href)

            if match:
                all_practices.append(match.group(1))

    return all_practices

def get_profiles_from_page(url) -> dict[any, list[str]]:
    profiles_url = []

    response = scraper.get(url)
    if response.status_code != 200:
        logger.info(f"Failed to retrieve page: {url}\n")
        logger.info(f"req: {response}\n")

        return profiles_url

    soup = bs(response.text, 'html.parser')
    ld_json = soup.find_all('script', type="application/ld+json")[-1]
    _json = json.loads(ld_json.string)

    for item in _json['@graph']:
        if item['@type'] == 'SearchResultsPage':
            for profile in item['mainEntity']['itemListElement']:
                profiles_url.append(profile['mainEntityOfPage']['url'])

    return {
        "has_next": soup.find('a', rel="next"),
        "profiles_url": profiles_url
    }

def get_all_profiles(practice, state, city) -> list[str]:
    base_url = f"https://lawyers.findlaw.com/lawyer/firm/{practice}/{state}/{city}"
    profiles_url = []

    while base_url:
        time.sleep(random.uniform(1, 5))
        parser = get_profiles_from_page(base_url)
        profiles_url.extend(parser['profiles_url'])

        if parser['has_next']:
            base_url = parser['has_next'].get('href')
        else:
            base_url = None

    return list(dict.fromkeys(profiles_url))

def get_profile_data(url) -> dict[str, any]:
    req = scraper.get(url)
    logger.info(f"Getting PROFILE: {url}")

    if req.status_code != 200:
        logger.info(f"Failed to retrieve page: Profile - {url}\n")
        logger.info(f"req: {req}\n")
        return {}

    soup = bs(req.text, 'html.parser')

    ld_json = soup.find_all('script', type="application/ld+json")[-1]
    profile = json.loads(ld_json.string)


    practice_areas = []
    pa_heading = soup.find('h4', string='Practice Areas')
    if pa_heading:
        li_tags = pa_heading.find_next('ul').find_all('li')
        for li in li_tags:
            practice_areas.append(li.text.strip())


    languages = []
    l_heading = soup.find('h4', string='Languages')
    if l_heading:
        li_tags = l_heading.find_next('ul').find_all('li')
        for li in li_tags:
            languages.append(li.text.strip())


    fax_numbers = []
    f_heading = soup.find('h4', string='Fax')
    if f_heading:
        li_tags = f_heading.find_next('ul').find_all('li')
        for li in li_tags:
            fax_numbers.append(li.text.strip())


    free_initial_consultation = None
    fic_heading = soup.find('h4', string='Offers Free Initial Consultation')
    if fic_heading:
        free_initial_consultation = fic_heading.find_next('p').text.strip()


    accepts_cc = None
    acc_heading = soup.find('h4', string='Accepts Credit Cards')
    if acc_heading:
        accepts_cc = acc_heading.find_next('p').text.strip()


    office_hours = None
    off_heading = soup.find('h4', string='Office Hours')
    if off_heading:
        office_hours = off_heading.find_next('p').text.strip()


    other_locations = []
    loc_heading = soup.find('h4', id='otherlocations')
    if loc_heading:
        locations = loc_heading.find_next('div', class_='block_content_body').find_all('p')
        for loc in locations:
            other_locations.append(loc.text.strip())


    achievements = []
    ach_heading = soup.find('h3', string='Achievements')
    if ach_heading:
        li_tags = ach_heading.find_next('ul').find_all('li')
        for li in li_tags:
            achievements.append(li.text.strip())


    articles = []
    art_heading = soup.find('h4', string='Articles')
    if art_heading:
        li_tags = art_heading.find_next('ul').find_all('li')
        for li in li_tags:
            a_tags = li.find_all('a')
            # this is almost always just one a tag, so, don't care big(o) notation
            for a in a_tags:
                articles.append(a.text.strip())


    profile['mainEntity']['practiceAreas'] = practice_areas
    profile['mainEntity']['languages'] = languages
    profile['mainEntity']['faxNumbers'] = fax_numbers
    profile['mainEntity']['freeInitialConsultation'] = free_initial_consultation
    profile['mainEntity']['acceptsCreditCards'] = accepts_cc
    profile['mainEntity']['officeHours'] = office_hours
    profile['mainEntity']['otherLocations'] = other_locations
    profile['mainEntity']['achievements'] = achievements
    profile['mainEntity']['articles'] = articles

    del profile['@context']

    return profile


states = get_all_states()
practices = get_all_practices()

with ThreadPoolExecutor(max_workers=4) as executor:
    for state in states:
        logger.info(f"Getting STATE: {state}\n")

        create_directory(state)
        cities = get_all_state_cities(state)

        for practice in practices:
            logger.info(f"Getting PRACTICE: {practice}\n")
            create_directory(state, practice)

            for city in cities:
                logger.info(f"Getting CITY: {city}\n")

                json_file_path = os.path.join("results", state, practice, f"{city}.json")
                if os.path.isfile(json_file_path):
                    logger.info(f"File already exists: {json_file_path}\n")
                    continue

                profiles_url = get_all_profiles(practice, state, city)
                profiles_data = list(executor.map(get_profile_data, profiles_url))


                logger.info(f"Writing to file: {json_file_path}\n")
                with open(json_file_path, 'w') as f:
                    json.dump(profiles_data, f, indent=2)