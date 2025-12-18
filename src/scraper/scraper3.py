"""
HELLOWORK SCRAPER PAR CATÉGORIES AVEC DESCRIPTION COMPLÈTE
Scrape les offres depuis les 4 catégories principales avec descriptions détaillées
Auteur: Assistant Claude
Date: Décembre 2024
"""

import time
import json
import re
import random
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    'pages_per_category': 15,  # Nombre de pages à scraper par catégorie
    'wait_timeout': 20,
    'output_dir': 'data',
    'debug_mode': True,
    'categories_to_scrape': [
        'Emploi Commerce',
        'Emploi Distribution', 
        'Emploi Comptabilité',
        'Emploi Ressources Humaines'
    ],
    'extract_full_description': True,  # Active l'extraction des descriptions complètes
    'description_wait': 3  # Temps d'attente sur la page de détail
}

# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================

class HelloworkCategoryScraper:
    """Scraper par catégories de la page d'accueil"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.driver = None
        self.all_offers = []
        self.seen_ids = set()
        self.category_links = {}
        
        Path(config['output_dir']).mkdir(exist_ok=True)
        
    def setup_driver(self) -> webdriver.Chrome:
        """Configure Selenium avec anti-détection"""
        print("\n🔧 Configuration de Selenium avec anti-détection...")
        
        options = Options()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Mode visible pour debug
        # options.add_argument('--headless=new')
        
        driver = webdriver.Chrome(options=options)
        
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            '''
        })
        
        driver.set_window_size(1920, 1080)
        print("✅ Selenium configuré\n")
        
        return driver
    
    def handle_login(self):
        """Gère la connexion manuelle"""
        print("\n" + "="*70)
        print("🔐 ÉTAPE 1 : CONNEXION")
        print("="*70)
        print("\n📋 INSTRUCTIONS:")
        print("   1. Une fenêtre de navigateur va s'ouvrir")
        print("   2. Connectez-vous à votre compte Hellowork")
        print("   3. Une fois connecté, revenez dans ce terminal")
        print("   4. Appuyez sur ENTRÉE pour continuer")
        print("\n⏳ Ouverture du navigateur...")
        
        self.driver.get("https://www.hellowork.com/fr-fr/")
        time.sleep(3)
        
        input("\n✋ Appuyez sur ENTRÉE après vous être connecté...")
        
        print("\n✅ Connexion confirmée")
        time.sleep(2)
    
    def find_category_links(self):
        """Trouve les liens des 4 catégories principales sur la page d'accueil"""
        print("\n" + "="*70)
        print("🔍 ÉTAPE 2 : IDENTIFICATION DES CATÉGORIES")
        print("="*70)
        
        try:
            self.driver.get("https://www.hellowork.com/fr-fr/")
            time.sleep(3)
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
            time.sleep(2)
            
            print("\n🔎 Recherche de la section 'On a classé tous nos jobs !'...")
            
            try:
                section_header = self.driver.find_element(By.XPATH, "//*[contains(text(), 'On a classé tous nos jobs')]")
                print("   ✓ Section trouvée")
                section_container = section_header.find_element(By.XPATH, "./ancestor::section | ./ancestor::div[@class]")
                links = section_container.find_elements(By.TAG_NAME, "a")
            except:
                print("   ⚠️  Section non trouvée par texte, recherche par structure...")
                links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/domaine_']")
            
            found_categories = {}
            
            for link in links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    
                    if text and href and '/domaine_' in href:
                        if any(cat.lower() in text.lower() for cat in self.config['categories_to_scrape']):
                            found_categories[text] = href
                            print(f"   ✓ Trouvé : {text}")
                            print(f"      URL : {href}")
                except:
                    continue
            
            if len(found_categories) < 4:
                print("\n   ⚠️  Méthode automatique incomplète, recherche manuelle...")
                
                default_categories = {
                    'Emploi Commerce': 'https://www.hellowork.com/fr-fr/emploi/domaine_commerce.html',
                    'Emploi Distribution': 'https://www.hellowork.com/fr-fr/emploi/domaine_distribution.html',
                    'Emploi Comptabilité': 'https://www.hellowork.com/fr-fr/emploi/domaine_comptabilite.html',
                    'Emploi Ressources Humaines': 'https://www.hellowork.com/fr-fr/emploi/domaine_ressources-humaines.html'
                }
                
                for cat_name, url in default_categories.items():
                    if cat_name not in found_categories:
                        found_categories[cat_name] = url
                        print(f"   ✓ Ajouté : {cat_name}")
            
            self.category_links = found_categories
            
            print(f"\n✅ Total : {len(self.category_links)} catégories identifiées")
            
            if len(self.category_links) == 0:
                print("\n⚠️  ATTENTION : Aucune catégorie trouvée !")
                return False
            
            return True
            
        except Exception as e:
            print(f"\n❌ Erreur lors de l'identification : {e}")
            import traceback
            if self.config['debug_mode']:
                print(traceback.format_exc())
            return False
    
    def extract_full_description(self, job_url: str) -> Optional[str]:
        """Extrait la description complète depuis la page de détail de l'offre"""
        current_window = self.driver.current_window_handle
        
        try:
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            self.driver.get(job_url)
            time.sleep(self.config['description_wait'])
            
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except:
                pass
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
            time.sleep(1)
            
            description_parts = []
            
            selectors = [
                "div[class*='description']",
                "div[class*='job-description']",
                "section[class*='description']",
                "div[data-testid*='description']",
                "article[class*='description']",
                "div.tw-prose",
                "div[class*='content']"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if len(text) > 100:
                            description_parts.append(text)
                except:
                    continue
            
            if not description_parts:
                try:
                    section_headers = self.driver.find_elements(By.CSS_SELECTOR, "h2, h3")
                    
                    for header in section_headers:
                        header_text = header.text.strip().lower()
                        
                        if any(keyword in header_text for keyword in [
                            'description', 'mission', 'profil', 'compétence', 
                            'qualification', 'responsabilité', 'poste', 'offre'
                        ]):
                            try:
                                parent = header.find_element(By.XPATH, "./parent::*")
                                siblings = parent.find_elements(By.XPATH, "./following-sibling::*")
                                
                                for sibling in siblings[:5]:
                                    text = sibling.text.strip()
                                    if len(text) > 50:
                                        description_parts.append(f"{header.text}:\n{text}")
                            except:
                                continue
                except:
                    pass
            
            if not description_parts:
                try:
                    main_content = self.driver.find_element(By.TAG_NAME, "main")
                    text = main_content.text.strip()
                    if len(text) > 200:
                        description_parts.append(text)
                except:
                    pass
            
            if description_parts:
                full_description = "\n\n".join(description_parts)
                
                lines = full_description.split('\n')
                unique_lines = []
                seen = set()
                
                for line in lines:
                    line_clean = line.strip()
                    if line_clean and line_clean not in seen:
                        unique_lines.append(line)
                        seen.add(line_clean)
                
                return '\n'.join(unique_lines)
            
            return None
            
        except Exception as e:
            if self.config['debug_mode']:
                print(f"\n         ⚠️  Erreur extraction description: {e}")
            return None
            
        finally:
            try:
                self.driver.close()
                self.driver.switch_to.window(current_window)
            except:
                pass
    
    def wait_and_find_job_cards(self) -> List:
        """Trouve les cartes d'offres"""
        time.sleep(3)
        self.smooth_scroll()
        time.sleep(2)
        
        selectors = [
            "div.tw-group.tw-h-full.tw-overflow-hidden.tw-bg-white.tw-rounded-sm",
            "article.job-card",
            "div.job-card",
            "article[data-testid*='job']",
            "a[href*='/fr-fr/emplois/']"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > 5:
                    return elements
            except:
                continue
        
        try:
            all_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/fr-fr/emplois/']")
            
            job_cards = []
            for link in all_links:
                try:
                    parent = link.find_element(By.XPATH, "./ancestor::div[contains(@class, 'tw-group')]")
                    if parent not in job_cards:
                        job_cards.append(parent)
                except:
                    if link not in job_cards:
                        job_cards.append(link)
            
            if job_cards:
                return job_cards
        except:
            pass
        
        return []
    
    def smooth_scroll(self):
        """Scroll progressif de la page"""
        try:
            for i in range(3):
                self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/3});")
                time.sleep(0.5)
        except:
            pass
    
    def extract_from_element(self, element, category_name: str) -> Optional[Dict]:
        """Extraction depuis une carte d'offre"""
        try:
            data = {'category': category_name}
            
            try:
                if element.tag_name == 'a':
                    link = element
                else:
                    link = element.find_element(By.CSS_SELECTOR, "a[href*='/fr-fr/emplois/']")
                
                url = link.get_attribute('href')
                data['url'] = url
                
                match = re.search(r'/emplois/(\d+)\.html', url)
                data['job_id'] = match.group(1) if match else f"unknown_{random.randint(1000,9999)}"
                
                if data['job_id'] in self.seen_ids:
                    return None
                    
            except:
                return None
            
            try:
                if element.tag_name == 'a':
                    parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'tw-group')]")
                    h3 = parent.find_element(By.CSS_SELECTOR, "h3")
                else:
                    h3 = element.find_element(By.CSS_SELECTOR, "h3")
                
                paragraphs = h3.find_elements(By.TAG_NAME, "p")
                
                if len(paragraphs) >= 1:
                    data['title'] = paragraphs[0].text.strip()
                if len(paragraphs) >= 2:
                    data['company'] = paragraphs[1].text.strip()
                else:
                    data['company'] = None
            except:
                data['title'] = None
                data['company'] = None
            
            if not data.get('title'):
                try:
                    title_attr = link.get_attribute('title')
                    if title_attr and ' - ' in title_attr:
                        parts = title_attr.split(' - ')
                        data['title'] = parts[0].strip()
                        if not data.get('company') and len(parts) >= 2:
                            data['company'] = parts[1].strip()
                    elif title_attr:
                        data['title'] = title_attr
                except:
                    pass
            
            try:
                if element.tag_name == 'a':
                    parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'tw-group')]")
                    tags = parent.find_elements(By.CSS_SELECTOR, "div.tw-readonly.tw-tag-secondary-s")
                else:
                    tags = element.find_elements(By.CSS_SELECTOR, "div.tw-readonly.tw-tag-secondary-s")
                
                for tag in tags:
                    text = tag.text.strip()
                    
                    if ' - ' in text and any(char.isdigit() for char in text):
                        data['location'] = text
                    elif text in ['CDI', 'CDD', 'Intérim', 'Stage', 'Alternance', 'Freelance', 'Temps partiel', 'Temps plein']:
                        data['contract_type'] = text
            except:
                pass
            
            if 'location' not in data:
                data['location'] = None
            if 'contract_type' not in data:
                data['contract_type'] = None
            
            try:
                if element.tag_name == 'a':
                    parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'tw-group')]")
                    salary_tags = parent.find_elements(By.CSS_SELECTOR, "div.tw-typo-s-bold")
                else:
                    salary_tags = element.find_elements(By.CSS_SELECTOR, "div.tw-typo-s-bold")
                
                for tag in salary_tags:
                    text = tag.text
                    if '€' in text or 'k' in text.lower():
                        data['salary'] = text.strip()
                        break
                else:
                    data['salary'] = None
            except:
                data['salary'] = None
            
            try:
                if element.tag_name == 'a':
                    parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'tw-group')]")
                    date_elem = parent.find_element(By.CSS_SELECTOR, "div.tw-text-grey-500")
                else:
                    date_elem = element.find_element(By.CSS_SELECTOR, "div.tw-text-grey-500")
                
                data['published_date'] = date_elem.text.strip()
            except:
                data['published_date'] = None
            
            try:
                if element.tag_name == 'a':
                    parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'tw-group')]")
                    data['short_description'] = parent.text[:300]
                else:
                    data['short_description'] = element.text[:300]
            except:
                data['short_description'] = None
            
            # EXTRACTION DE LA DESCRIPTION COMPLÈTE
            if self.config['extract_full_description'] and data.get('url'):
                print(f"\n         📄 Extraction description...", end=" ", flush=True)
                full_desc = self.extract_full_description(data['url'])
                
                if full_desc:
                    data['description'] = full_desc
                    print(f"✓ ({len(full_desc)} car.)")
                else:
                    data['description'] = data.get('short_description', None)
                    print("⚠️")
            else:
                data['description'] = data.get('short_description', None)
            
            try:
                text_lower = (element.text if element.tag_name != 'a' else 
                             element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'tw-group')]").text).lower()
                data['remote'] = any(kw in text_lower for kw in ['télétravail', 'remote', 'home office', 'hybride'])
            except:
                data['remote'] = False
            
            try:
                text = element.text if element.tag_name != 'a' else element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'tw-group')]").text
                exp_pattern = r'(\d+)\s*(?:ans?|années?)\s*(?:d\'expérience|expérience|exp)'
                exp_match = re.search(exp_pattern, text, re.IGNORECASE)
                data['experience'] = exp_match.group(0) if exp_match else None
            except:
                data['experience'] = None
            
            data['scraped_at'] = datetime.now().isoformat()
            
            if not data.get('title'):
                return None
            
            self.seen_ids.add(data['job_id'])
            return data
            
        except Exception as e:
            if self.config['debug_mode']:
                print(f"         ⚠️  Erreur: {e}")
            return None
    
    def scrape_category_page(self, category_name: str, url: str, page: int) -> List[Dict]:
        """Scrape une page d'une catégorie"""
        page_url = f"{url}?p={page}" if page > 1 else url
        
        print(f"      📄 Page {page}/{self.config['pages_per_category']}...", end=" ", flush=True)
        
        try:
            self.driver.get(page_url)
            time.sleep(random.uniform(3, 5))
            
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except:
                pass
            
            elements = self.wait_and_find_job_cards()
            
            if not elements:
                print("⚠️  Aucune offre")
                return []
            
            offers = []
            for elem in elements:
                data = self.extract_from_element(elem, category_name)
                if data:
                    offers.append(data)
            
            print(f"✓ {len(offers)} offres")
            
            return offers
            
        except Exception as e:
            print(f"❌ Erreur: {str(e)[:40]}")
            return []
    
    def scrape_category(self, category_name: str, url: str) -> List[Dict]:
        """Scrape toutes les pages d'une catégorie"""
        print(f"\n{'='*70}")
        print(f"📂 CATÉGORIE: {category_name}")
        print(f"🔗 URL: {url}")
        print(f"{'='*70}")
        
        category_offers = []
        
        for page in range(1, self.config['pages_per_category'] + 1):
            offers = self.scrape_category_page(category_name, url, page)
            category_offers.extend(offers)
            
            if page >= 3 and len(category_offers) == 0:
                print(f"      ⚠️  Aucune offre après {page} pages")
                break
            
            if page < self.config['pages_per_category']:
                time.sleep(random.uniform(2, 4))
        
        print(f"\n   ✅ Total {category_name}: {len(category_offers)} offres")
        return category_offers
    
    def run(self):
        """Lance le scraping complet"""
        print("\n" + "="*70)
        print("   HELLOWORK SCRAPER - DESCRIPTIONS COMPLÈTES")
        print("="*70)
        
        try:
            self.driver = self.setup_driver()
            self.handle_login()
            
            if not self.find_category_links():
                print("\n❌ Impossible de continuer")
                return
            
            print("\n" + "="*70)
            print("🚀 ÉTAPE 3 : SCRAPING DES CATÉGORIES")
            print("="*70)
            
            for idx, (cat_name, url) in enumerate(self.category_links.items(), 1):
                print(f"\n[{idx}/{len(self.category_links)}] {cat_name}...")
                
                offers = self.scrape_category(cat_name, url)
                self.all_offers.extend(offers)
                
                if idx < len(self.category_links):
                    print(f"\n   ⏸️  Pause 10s...")
                    time.sleep(10)
            
            self.save_results()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interruption")
            if self.all_offers:
                self.save_results()
            
        except Exception as e:
            print(f"\n❌ ERREUR: {e}")
            if self.all_offers:
                self.save_results()
            
        finally:
            if self.driver:
                self.driver.quit()
                print("\n✅ Driver fermé")
    
    def save_results(self):
        """Sauvegarde les résultats"""
        if not self.all_offers:
            print("\n⚠️  Aucune offre à sauvegarder")
            return
        
        print(f"\n{'='*70}")
        print(f"💾 SAUVEGARDE DES RÉSULTATS")
        print(f"{'='*70}")
        
        df = pd.DataFrame(self.all_offers)
        
        print(f"\n📊 STATISTIQUES:")
        print(f"   • Total: {len(df)} offres")
        print(f"   • Uniques: {df['job_id'].nunique()}")
        
        if 'description' in df.columns:
            desc_full = df['description'].notna().sum()
            desc_avg = df[df['description'].notna()]['description'].str.len().mean()
            print(f"   • Descriptions: {desc_full}/{len(df)} ({desc_full/len(df)*100:.1f}%)")
            print(f"   • Longueur moy: {desc_avg:.0f} car.")
        
        print(f"\n📂 PAR CATÉGORIE:")
        for cat, count in df['category'].value_counts().items():
            print(f"   • {cat}: {count}")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        csv_path = Path(self.config['output_dir']) / f'hellowork_{timestamp}.csv'
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ CSV: {csv_path}")
        
        json_path = Path(self.config['output_dir']) / f'hellowork_{timestamp}.json'
        df.to_json(json_path, orient='records', force_ascii=False, indent=2)
        print(f"✅ JSON: {json_path}")
        
        try:
            excel_path = Path(self.config['output_dir']) / f'hellowork_{timestamp}.xlsx'
            df.to_excel(excel_path, index=False, engine='openpyxl')
            print(f"✅ Excel: {excel_path}")
        except:
            pass
        
        print(f"\n{'='*70}")
        print("✨ TERMINÉ!")

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    scraper = HelloworkCategoryScraper(CONFIG)
    scraper.run()