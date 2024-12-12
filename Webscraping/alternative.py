import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
import logging
import threading
import time
import random
import json

# Initialisation du logger
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configuration avancée pour Selenium
def configure_driver(proxy=None):
    options = uc.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'user-agent={UserAgent().random}')
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    driver = uc.Chrome(options=options)
    # Stealth mode
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """
    })
    return driver

# Fonction pour extraire les cours d'une plateforme
def scrape_courses(source, results, proxy=None):
    logging.info(f"Lancement du scraping pour {source['type']}...")
    driver = configure_driver(proxy)
    try:
        driver.get(source['url'])
        time.sleep(random.uniform(3, 6))

        wait = WebDriverWait(driver, 20)
        course_elements = wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, source['css_selector'])
            )
        )

        platform_results = []
        for element in course_elements[:10]:
            try:
                titre_elem = element.find_element(By.CSS_SELECTOR, source.get('title_selector', 'h3'))
                lien_elem = element.find_element(By.CSS_SELECTOR, source.get('link_selector', 'a'))
                platform_results.append({
                    'titre': titre_elem.text.strip(),
                    'url': lien_elem.get_attribute('href'),
                    'plateforme': source['type'].capitalize()
                })
                time.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                logging.warning(f"Erreur lors de l'extraction d'un cours sur {source['type']} : {e}")

        results.extend(platform_results)
        logging.info(f"Scraping terminé pour {source['type']} : {len(platform_results)} cours récupérés.")
    
    except Exception as e:
        logging.error(f"Erreur sur {source['type']} : {e}")
    
    finally:
        try:
            driver.quit()
        except Exception as e:
            logging.warning(f"Erreur lors de la fermeture du driver : {e}")

# Liste des plateformes à scraper
sources = [
    {
        'url': 'https://www.udemy.com/courses/development/',
        'type': 'udemy',
        'css_selector': 'div[data-purpose="course-card-title"]',
        'title_selector': 'h3',
        'link_selector': 'a'
    },
    {
        'url': 'https://fr.coursera.org/browse/computer-science',
        'type': 'coursera',
        'css_selector': 'div.css-1c2m8e5 > a',
        'title_selector': '.card-title',
        'link_selector': 'a'
    }
]

# Fonction principale pour gérer les threads
def advanced_course_scraper(use_proxies=False):
    proxies = ['proxy1:port', 'proxy2:port'] if use_proxies else [None]
    results = []
    threads = []

    # Lancement des threads
    for source in sources:
        proxy = random.choice(proxies)
        thread = threading.Thread(target=scrape_courses, args=(source, results, proxy))
        threads.append(thread)
        thread.start()

    # Attente de la fin des threads
    for thread in threads:
        thread.join()

    logging.info(f"Nombre total de cours récupérés : {len(results)}")
    return results

# Exécution du script
if __name__ == "__main__":
    use_proxies = False  # Activez les proxys si nécessaire
    courses = advanced_course_scraper(use_proxies)
    print(json.dumps(courses, indent=2, ensure_ascii=False))
