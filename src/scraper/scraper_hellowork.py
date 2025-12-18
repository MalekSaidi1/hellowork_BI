import os
import csv
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# --- Options du navigateur ---
options = Options()
options.add_argument("--headless")  # mode sans interface
options.add_argument("--window-size=1920,1080")

# --- Chemin absolu vers chromedriver ---
script_dir = os.path.dirname(os.path.abspath(__file__))
chromedriver_path = os.path.join(script_dir, "chromedriver.exe")

service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=options)

# --- Configuration scraping ---
base_url = "https://www.hellowork.com/fr-fr/emploi.html"
max_pages = 10
page = 1
data = []

print(">>> DÉBUT SCRAPING HELLOWORK <<<\n")

while page <= max_pages:
    print(f">> Ouverture de la page {page} : {base_url}?page={page}")
    driver.get(f"{base_url}?page={page}")
    time.sleep(3)

    # Cliquer sur "Voir toutes les offres"
    try:
        voir_toutes_btn = driver.find_element(By.CSS_SELECTOR, 'span.tw-btn-primary-xl.tw-mt-6.sm\\:tw-mt-8.tw-place-self-start')
        driver.execute_script("arguments[0].click();", voir_toutes_btn)
        time.sleep(3)
        print(f"Page {page} : Bouton 'Voir toutes les offres' cliqué !")
    except:
        print(f"Page {page} : Bouton 'Voir toutes les offres' non trouvé")

    # Scroll pour charger toutes les offres
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # Liens des offres
    offres_elements = driver.find_elements(By.CSS_SELECTOR, 'a[data-cy="offerTitle"]')
    if not offres_elements:
        print(f"Page {page} : Aucune offre trouvée")
        break

    offres_links = [offre.get_attribute("href") for offre in offres_elements]
    print(f"Page {page} : {len(offres_links)} offres trouvées")

    # Scraper chaque offre
    for lien in offres_links:
        driver.get(lien)
        time.sleep(2)

        # --- CHAMPS HABITUELS ---
        try:
            titre = driver.find_element(By.CSS_SELECTOR, 'span[data-cy="jobTitle"]').text
        except:
            titre = "N/A"

        try:
            entreprise = driver.find_element(By.CSS_SELECTOR, 'a.tw-link-underline').get_attribute("title")
        except:
            entreprise = "N/A"

        try:
            tags = driver.find_elements(By.CSS_SELECTOR, 'li.tw-tag-grey-s.tw-readonly')
            localisation = tags[0].text if len(tags) > 0 else "N/A"
            type_contrat = tags[1].text if len(tags) > 1 else "N/A"
        except:
            localisation = "N/A"
            type_contrat = "N/A"

        try:
            tags2 = driver.find_elements(By.CSS_SELECTOR, 'li.tw-block.tw-tag-secondary-s.tw-border-0.tw-readonly')
            niveau_etudes = tags2[0].text if len(tags2) > 0 else "N/A"
            experience = tags2[1].text if len(tags2) > 1 else "N/A"
        except:
            niveau_etudes = "N/A"
            experience = "N/A"

        try:
            date_text = driver.find_element(By.CSS_SELECTOR, 'span.tw-block.tw-typo-xs.tw-text-grey-500.tw-break-words').text
            match = re.search(r'Publiée le (\d{2}/\d{2}/\d{4})', date_text)
            date_pub = match.group(1) if match else "N/A"
        except:
            date_pub = "N/A"

        try:
            salaire_btn = driver.find_element(By.CSS_SELECTOR, 'button[data-cy="salary-tag-button"]')
            salaire = salaire_btn.text.strip()
        except:
            salaire = "N/A"

        # --- NOUVELLE PARTIE : EXTRACTION DE LA DESCRIPTION ---
        try:
            # bloc principal de description
            desc_block = driver.find_element(By.CSS_SELECTOR, 'div[data-cy="jobDescription"]')
            description_element = driver.find_element(By.CSS_SELECTOR, 'div[data-cy="jobDescription"]')
            description = description_element.text.strip()

        except:
            description = "Non renseignée"

        # --- SAUVEGARDE DANS LA LISTE ---
        data.append([
            titre,
            entreprise,
            localisation,
            type_contrat,
            niveau_etudes,
            experience,
            date_pub,
            salaire,
            lien,
            description  # ✔ nouvelle colonne
        ])

        print(f"Scraped: {titre}")

    page += 1

# --- SAUVEGARDE DU CSV ---
csv_file = os.path.join(script_dir, "../../data/offres_hellowork_full.csv")

with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Titre",
        "Entreprise",
        "Localisation",
        "Type contrat",
        "Niveau d'études",
        "Expérience",
        "Date Publication",
        "Salaire",
        "Lien Offre",
        "Description"
    ])
    writer.writerows(data)

driver.quit()
print("\n>>> Scraping terminé !")
print(f"CSV généré avec succès : {csv_file}")
