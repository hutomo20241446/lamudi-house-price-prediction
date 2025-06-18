from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import csv
import time
import random
import tempfile
import os
import shutil

def initialize_webdriver():
    """Inisialisasi WebDriver dengan direktori data pengguna yang unik."""
    options = webdriver.ChromeOptions()
    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")
    options.add_argument('--user-agent=' + random.choice([
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.2210.144',
        'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    ]))
    # options.add_argument('--headless') # Anda bisa aktifkan headless jika perlu
    driver = webdriver.Chrome(options=options)
    driver.temp_user_data_dir = temp_dir # Simpan direktori sementara untuk dihapus nanti
    return driver

def extract_listing_data_selenium(listing_element):
    """Mengambil data listing properti dari elemen Selenium, termasuk luas rumah dan tanah."""
    listing = {
        "Title": "Unknown Listing",
        "Price": "Price Unavailable",
        "Bedrooms": "N/A",
        "Living Size(m²)": "N/A",
        "Land Size(m²)": "N/A",
        "Location": "N/A",
        "Timestamp": datetime.now().isoformat()
    }

    try:
        title_element = listing_element.find_element(By.CSS_SELECTOR, 'h3.ListingCellItem_listingTitle__lHzmY')
        listing["Title"] = title_element.text.strip()
    except NoSuchElementException:
        pass

    try:
        price_element = listing_element.find_element(By.CSS_SELECTOR, 'span.ListingCellItem_listingPrice___oTdU')
        listing["Price"] = price_element.text.strip().replace('\xa0', ' ')
    except NoSuchElementException:
        pass

    try:
        location_element = listing_element.find_element(By.CSS_SELECTOR, 'div.ListingCellItem_listingLocation__1wjst span.ListingCellItem_addressLine__hp5ZO')
        listing["Location"] = location_element.text.strip()
    except NoSuchElementException:
        pass

    try:
        attributes_div = listing_element.find_element(By.CSS_SELECTOR, 'div.ListingCellItem_listingAttribute__7N9Hm')
        attribute_items = attributes_div.find_elements(By.CSS_SELECTOR, 'div.ListingCellItem_attributeItem__d9TFw.ListingCellItem_withIcon__mPUst')
        for item in attribute_items:
            try:
                icon_span = item.find_element(By.CSS_SELECTOR, 'span')
                value_span = item.find_element(By.XPATH, './/span[2]') # Ambil span kedua yang berisi nilai
                if "icon-bedrooms" in icon_span.get_attribute("class"):
                    listing["Bedrooms"] = value_span.text.strip()
                elif "icon-livingsize" in icon_span.get_attribute("class"):
                    # Ekstrak hanya angka dari string seperti "200m²"
                    listing["Living Size(m²)"] = value_span.text.strip().replace('m²', '')
                elif "icon-land_size" in icon_span.get_attribute("class"):
                    # Ekstrak hanya angka dari string seperti "100m²"
                    listing["Land Size(m²)"] = value_span.text.strip().replace('m²', '')
            except NoSuchElementException:
                continue
    except NoSuchElementException:
        pass

    return listing


def scrape_lamudi_listings_selenium(base_url, delay=3, max_pages=None, max_retries=3):
    """Fungsi utama untuk mengambil semua data listing properti menggunakan Selenium dengan klik tombol next."""
    driver = initialize_webdriver()
    data = []
    page_number = 1

    try:
        driver.get(base_url)
        while True:
            print(f"Scraping halaman (Selenium) ke-{page_number}")

            retries = 0
            while retries < max_retries:
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.ListingCellItem_unstyledLink__nekX6.ListingCellItem_listingInfo__vdWNk'))
                    )
                    listing_elements = driver.find_elements(By.CSS_SELECTOR, 'a.ListingCellItem_unstyledLink__nekX6.ListingCellItem_listingInfo__vdWNk')

                    if not listing_elements:
                        print("Tidak menemukan listing di halaman ini, mungkin sudah mencapai halaman terakhir.")
                        return data

                    for listing_element in listing_elements:
                        listing = extract_listing_data_selenium(listing_element)
                        data.append(listing)

                    # Cek apakah sudah mencapai halaman maksimum
                    if max_pages and page_number >= max_pages:
                        return data

                    # Coba cari tombol Next
                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, 'a.Pagination_navigationButton__c6HK6 > span.icon-play-right')
                        parent_link = next_button.find_element(By.XPATH, './parent::a')

                        # Klik tombol next
                        driver.execute_script("arguments[0].click();", parent_link)

                        page_number += 1

                        # Random delay sebelum scraping halaman berikutnya
                        time.sleep(delay + random.uniform(2, 5))
                        break  # keluar dari retry-loop dan lanjut ke halaman berikutnya

                    except Exception as e:
                        print("Tidak menemukan tombol Next Page. Mungkin sudah halaman terakhir.")
                        return data

                except TimeoutException:
                    retries += 1
                    print(f"Timeout saat memuat halaman ke-{page_number}. Retry {retries}/{max_retries}...")
                    time.sleep(5)
                except Exception as e:
                    print(f"Terjadi kesalahan lain: {e}")
                    return data

            if retries == max_retries:
                print(f"Gagal memuat halaman ke-{page_number} setelah {max_retries} percobaan. Menghentikan proses scraping.")
                break

    finally:
        driver.quit()
        if hasattr(driver, 'temp_user_data_dir') and os.path.exists(driver.temp_user_data_dir):
            shutil.rmtree(driver.temp_user_data_dir)

    return data



def save_to_csv(data, filename='scraping_selenium.csv'):
    """Menyimpan data ke file CSV."""
    if not data:
        print("Tidak ada data untuk disimpan.")
        return

    keys = data[0].keys()

    with open(filename, 'w', newline='', encoding='utf-8-sig') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)

    print(f"Data berhasil disimpan ke {filename}")

if __name__ == "__main__":
    base_url = "https://www.lamudi.co.id/jual/rumah"

    # Scrape data dari Lamudi menggunakan Selenium
    print("Memulai proses scraping menggunakan Selenium...")
    listings = scrape_lamudi_listings_selenium(base_url, delay=5, max_pages=50)  # Contoh dengan 2 halaman

    # Tampilkan hasil di console
    print("\nHasil Scraping (Selenium):")
    if listings:
        for idx, listing in enumerate(listings, 1):
            print(f"{idx}. {listing['Title']} - {listing['Price']} - Kamar Tidur: {listing['Bedrooms']} - Luas Rumah: {listing['Living Size(m²)']} m² - Luas Tanah: {listing['Land Size(m²)']} m² - Lokasi: {listing['Location']}")

        # Simpan ke CSV
        save_to_csv(listings, filename='lamudi_house_price_scraping.csv')
    else:
        print("Tidak ada data yang berhasil di-scrape menggunakan Selenium.")