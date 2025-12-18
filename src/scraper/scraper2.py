import os
import csv
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# =============================================================================
# CONFIGURATION
# =============================================================================

# Options du navigateur
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

# Chemins
script_dir = os.path.dirname(os.path.abspath(__file__))
chromedriver_path = os.path.join(script_dir, "chromedriver.exe")
csv_file = os.path.join(script_dir, "../../data/offres_hellowork_full.csv")

# Paramètres scraping
base_url = "https://www.hellowork.com/fr-fr/emploi.html"
max_pages = 10
page = 1
data = []

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def safe_find_element(driver, by, selector, default="N/A"):
    """Trouve un élément de manière sécurisée"""
    try:
        element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((by, selector))
        )
        return element.text.strip() if element.text else default
    except:
        return default


def close_cookie_banner(driver):
    """Ferme le bandeau de cookies s'il est présent"""
    try:
        # Attendre un peu que le bandeau apparaisse
        time.sleep(1)
        
        # Essayer plusieurs sélecteurs de boutons cookie
        cookie_selectors = [
            "button[id*='accept']",
            "button[id*='cookie']",
            "button[class*='accept']",
            "button[class*='cookie']",
            "//*[contains(text(), 'Accepter')]",
            "//*[contains(text(), 'Refuser')]",
            "//*[contains(text(), 'Fermer')]"
        ]
        
        for selector in cookie_selectors:
            try:
                if selector.startswith("/"):
                    buttons = driver.find_elements(By.XPATH, selector)
                else:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for button in buttons[:1]:  # Cliquer sur le premier trouvé
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
                        print("  ✓ Bandeau cookie fermé")
                        return True
                    except:
                        continue
            except:
                continue
        
        # Si aucun bouton trouvé, supprimer les overlays avec JavaScript
        driver.execute_script("""
            var overlays = document.querySelectorAll('[class*="cookie"], [class*="consent"], [id*="cookie"], [class*="gdpr"]');
            overlays.forEach(function(el) {
                if (el) el.remove();
            });
        """)
        
    except Exception as e:
        print(f"  ⚠ Erreur fermeture cookie: {e}")
    
    return False


def extract_description(driver):
    """
    Extrait la description de l'offre (VERSION CORRIGÉE)
    Évite les bandeaux cookie et extrait le vrai contenu
    """
    try:
        # Attendre le chargement
        time.sleep(2)
        
        # Supprimer les éléments parasites avec JavaScript
        driver.execute_script("""
            // Supprimer overlays et bandeaux
            var toRemove = document.querySelectorAll('[class*="cookie"], [class*="consent"], [id*="cookie"], [class*="banner"]');
            toRemove.forEach(el => el.remove());
        """)
        
        # Récupérer le HTML de la page
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Supprimer les éléments inutiles
        for element in soup.select('header, footer, nav, [class*="cookie"], [class*="banner"]'):
            element.decompose()
        
        # Liste de sélecteurs par priorité
        selectors = [
            'div[data-cy="jobDescription"]',
            'article[class*="job"]',
            'section[class*="description"]',
            'div[class*="job-description"]',
            'main section',
        ]
        
        for selector in selectors:
            desc_element = soup.select_one(selector)
            
            if desc_element:
                # Extraire tout le texte
                text = desc_element.get_text(separator='\n', strip=True)
                
                # Validation : Vérifier que ce n'est PAS le message cookie
                invalid_phrases = [
                    "ces traceurs sont nécessaires",
                    "au bon fonctionnement de nos services",
                    "cookies",
                    "accepter",
                    "refuser",
                    "paramètres de confidentialité",
                    "en savoir plus"
                ]
                
                text_lower = text.lower()
                
                # Si le texte contient uniquement des phrases cookie, ignorer
                if any(phrase in text_lower for phrase in invalid_phrases) and len(text) < 200:
                    continue
                
                # Si le texte est valide et assez long
                if len(text) > 100:
                    # Nettoyer les phrases cookie si présentes dans un texte plus long
                    lines = text.split('\n')
                    clean_lines = []
                    
                    for line in lines:
                        line_lower = line.lower().strip()
                        # Garder la ligne si elle ne contient pas de phrases cookie
                        if not any(phrase in line_lower for phrase in invalid_phrases):
                            if len(line.strip()) > 0:
                                clean_lines.append(line.strip())
                    
                    result = '\n'.join(clean_lines)
                    
                    if len(result) > 100:
                        return result
        
        # Si aucun sélecteur ne fonctionne, dernier recours
        body = soup.find('body')
        if body:
            text = body.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 30]
            
            # Filtrer les lignes avec mots-clés cookie
            clean_lines = []
            for line in lines:
                if not any(phrase in line.lower() for phrase in invalid_phrases):
                    clean_lines.append(line)
            
            result = '\n'.join(clean_lines)
            if len(result) > 100:
                return result
        
        return "Non renseignée"
        
    except Exception as e:
        print(f"  ⚠ Erreur extraction description: {e}")
        return "Non renseignée"


def save_progress(data, filepath):
    """Sauvegarde progressive des données"""
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Titre", "Entreprise", "Localisation", "Type contrat",
                "Niveau d'études", "Expérience", "Date Publication",
                "Salaire", "Lien Offre", "Description"
            ])
            writer.writerows(data)
    except Exception as e:
        print(f"  ⚠ Erreur sauvegarde: {e}")


# =============================================================================
# INITIALISATION
# =============================================================================

service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=options)

print("=" * 70)
print(">>> DÉBUT SCRAPING HELLOWORK (VERSION CORRIGÉE) <<<")
print("=" * 70)

# =============================================================================
# BOUCLE PRINCIPALE
# =============================================================================

try:
    while page <= max_pages:
        print(f"\n{'='*70}")
        print(f"📄 PAGE {page}/{max_pages}")
        print(f"{'='*70}")
        
        driver.get(f"{base_url}?page={page}")
        time.sleep(3)
        
        # Fermer le bandeau cookie dès l'arrivée sur la page
        close_cookie_banner(driver)
        
        # Cliquer sur "Voir toutes les offres"
        try:
            voir_toutes_btn = driver.find_element(
                By.CSS_SELECTOR, 
                'span.tw-btn-primary-xl.tw-mt-6.sm\\:tw-mt-8.tw-place-self-start'
            )
            driver.execute_script("arguments[0].click();", voir_toutes_btn)
            time.sleep(3)
            print("✓ Bouton 'Voir toutes les offres' cliqué")
        except:
            print("ℹ Bouton 'Voir toutes les offres' non trouvé")
        
        # Scroll progressif
        print("⏳ Chargement des offres...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 10
        
        while scroll_attempts < max_scroll_attempts:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1
        
        # Récupération des liens
        offres_elements = driver.find_elements(By.CSS_SELECTOR, 'a[data-cy="offerTitle"]')
        
        if not offres_elements:
            print("❌ Aucune offre trouvée sur cette page")
            break
        
        offres_links = list(set([offre.get_attribute("href") for offre in offres_elements]))
        print(f"✓ {len(offres_links)} offres uniques trouvées")
        
        # =============================================================================
        # SCRAPING DE CHAQUE OFFRE
        # =============================================================================
        
        for idx, lien in enumerate(offres_links, 1):
            try:
                print(f"\n  [{idx}/{len(offres_links)}] {lien[:60]}...")
                driver.get(lien)
                time.sleep(2)
                
                # Fermer le bandeau cookie sur la page de l'offre
                close_cookie_banner(driver)
                
                # Extraction des champs de base
                titre = safe_find_element(driver, By.CSS_SELECTOR, 'span[data-cy="jobTitle"]')
                
                try:
                    entreprise = driver.find_element(By.CSS_SELECTOR, 'a.tw-link-underline').get_attribute("title")
                except:
                    entreprise = "N/A"
                
                # Tags (localisation, contrat)


                try:
                    tags = driver.find_elements(By.CSS_SELECTOR, 'li.tw-tag-grey-s.tw-readonly')
                    localisation = tags[0].text if len(tags) > 0 else "N/A"
                    type_contrat = tags[1].text if len(tags) > 1 else "N/A"
                except:
                    localisation = "N/A"
                    type_contrat = "N/A"
                
                # Tags secondaires (études, expérience)
                try:
                    tags2 = driver.find_elements(By.CSS_SELECTOR, 'li.tw-block.tw-tag-secondary-s.tw-border-0.tw-readonly')
                    niveau_etudes = tags2[0].text if len(tags2) > 0 else "N/A"
                    experience = tags2[1].text if len(tags2) > 1 else "N/A"
                except:
                    niveau_etudes = "N/A"
                    experience = "N/A"
                
                # Date de publication
                try:
                    date_text = driver.find_element(By.CSS_SELECTOR, 'span.tw-block.tw-typo-xs.tw-text-grey-500.tw-break-words').text
                    match = re.search(r'Publiée le (\d{2}/\d{2}/\d{4})', date_text)
                    date_pub = match.group(1) if match else "N/A"
                except:
                    date_pub = "N/A"
                
                # Salaire
                try:
                    salaire_btn = driver.find_element(By.CSS_SELECTOR, 'button[data-cy="salary-tag-button"]')
                    salaire = salaire_btn.text.strip()
                except:
                    salaire = "N/A"
                
                # ⭐ DESCRIPTION (CORRIGÉE)
                description = extract_description(driver)
                
                # Validation de la description
                desc_preview = description[:80] + "..." if len(description) > 80 else description
                if "ces traceurs" in description.lower():
                    print(f"  ⚠ Description = message cookie (échec)")
                else:
                    print(f"  ✓ Description OK: {desc_preview}")
                
                # Sauvegarde
                data.append([
                    titre, entreprise, localisation, type_contrat,
                    niveau_etudes, experience, date_pub, salaire,
                    lien, description
                ])
                
                print(f"  ✓ {titre[:50]}")
                
                # Sauvegarde progressive tous les 10 scrapes
                if len(data) % 10 == 0:
                    save_progress(data, csv_file)
                    print(f"  💾 Sauvegarde: {len(data)} offres")
                
            except Exception as e:
                print(f"  ❌ Erreur: {str(e)}")
                continue
        
        page += 1

except KeyboardInterrupt:
    print("\n\n⚠ Scraping interrompu par l'utilisateur")
except Exception as e:
    print(f"\n\n❌ Erreur critique: {str(e)}")
finally:
    # Sauvegarde finale
    save_progress(data, csv_file)
    driver.quit()
    
    print("\n" + "=" * 70)
    print(">>> SCRAPING TERMINÉ <<<")
    print("=" * 70)
    print(f"✓ Total d'offres scrapées: {len(data)}")
    print(f"✓ Fichier généré: {csv_file}")
    print("=" * 70)