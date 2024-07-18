import csv
import requests
from bs4 import BeautifulSoup, SoupStrainer
from fuzzywuzzy import fuzz
import cfscrape
import operator
import concurrent.futures
import argparse
from lxml import html
import logging

# Configuring logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

cfscrape.DEFAULT_CIPHERS = 'TLS_AES_256_GCM_SHA384:ECDHE-ECDSA-AES256-SHA384'
scraper = cfscrape.create_scraper()

HEADER = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
}
MIN_RATIO = 0.3333

def getDomainCrunchbase(link):
    try:
        c = scraper.get(link).content
        tree = html.fromstring(c)
        url = tree.xpath("//span[contains(text(), 'Website')]/../../../following::span[1]//a/@title")
        if url:
            l = clean_url(url[0])
            return [l.lower()]
    except Exception as e:
        logging.error(f"Error getting domain from Crunchbase: {e}")
    return []

def getDomainOwler(link):
    try:
        only_a_tags = SoupStrainer('div', {'class': 'website'})
        c = scraper.get(link).content
        soup = BeautifulSoup(c, 'html.parser', parse_only=only_a_tags)
        if soup.p:
            l = clean_url(soup.p.a.get('href'))
            return [l.lower()]
    except Exception as e:
        logging.error(f"Error getting domain from Owler: {e}")
    return []

def getDomainAngel(link):
    try:
        only_a_tags = SoupStrainer('li', {'class': 'websiteLink_daf63'})
        c = scraper.get(link).content
        soup = BeautifulSoup(c, 'html.parser', parse_only=only_a_tags)
        if soup.a:
            l = clean_url(soup.a.get('href'))
            return [l.lower()]
    except Exception as e:
        logging.error(f"Error getting domain from AngelList: {e}")
    return []

def clean_url(url):
    if 'www.' in url:
        url = url.split('www.')[1]
    if '//' in url:
        url = url.split('//')[1]
    if '/' in url:
        url = url.split('/')[0]
    return url

def getDomain(i, company_search):
    temp = []
    temp1, temp3, temp4 = [], [], []
    only_div_tags = SoupStrainer('li', {'class': 'b_algo'})
    if i == 1:
        res = requests.get(f'https://www.bing.com/search?q={company_search}', headers=HEADER, timeout=10)
        if res.status_code == 200:
            c = res.content
            soup = BeautifulSoup(c, 'html.parser', parse_only=only_div_tags)
            for h2 in soup.findAll('h2'):
                if h2.a:
                    link = clean_url(h2.a['href'])
                    if link not in temp:
                        temp.append(link.lower())
    elif i == 2:
        res = requests.get(f'https://www.bing.com/search?q=crunchbase:%20{company_search}', headers=HEADER, timeout=10)
        if res.status_code == 200:
            c = res.content
            soup = BeautifulSoup(c, 'html.parser', parse_only=only_div_tags)
            for h2 in soup.findAll('h2'):
                if h2.a:
                    link = h2.a['href']
                    if 'www.crunchbase.com/organization/' in link:
                        temp1.append(link)
            with concurrent.futures.ThreadPoolExecutor(max_workers=500) as executor:
                temp1 = list(executor.map(getDomainCrunchbase, temp1))
    elif i == 4:
        res = requests.get(f'https://www.bing.com/search?q=angellist:%20{company_search}', headers=HEADER, timeout=10)
        if res.status_code == 200:
            c = res.content
            soup = BeautifulSoup(c, 'html.parser', parse_only=only_div_tags)
            for h2 in soup.findAll('h2'):
                if h2.a:
                    link = h2.a['href']
                    if '//angel.co/' in link and '/jobs/' not in link:
                        if '/company/' in link or '/l/' in link:
                            temp4.append(link)
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                temp4 = list(executor.map(getDomainAngel, temp4))
    elif i == 5:
        res = requests.get(f'https://www.bing.com/search?q=owler:%20{company_search}', headers=HEADER, timeout=10)
        if res.status_code == 200:
            c = res.content
            soup = BeautifulSoup(c, 'html.parser', parse_only=only_div_tags)
            for h2 in soup.findAll('h2'):
                if h2.a:
                    link = h2.a['href']
                    if 'www.owler.com/company' in link:
                        temp3.append(link)
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                temp3 = list(executor.map(getDomainOwler, temp3))
    dom_list = temp + temp1 + temp3 + temp4
    return [x for x in dom_list if x]

def getResults(company_name):
    company_search = company_name.replace(' ', '%20')
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        data = list(executor.map(getDomain, range(1, 6), [company_search]*5))
    doms = {}
    for i in data:
        for j in i:
            if isinstance(j, list):
                j = j[0]
            if j in doms:
                doms[j] += 1
            else:
                doms[j] = 1
    try:
        most_probable_domain = max(doms.items(), key=operator.itemgetter(1))[0]
    except Exception as e:
        logging.error(f"Error determining most probable domain: {e}")
        exit()
    cnt = 0
    for i in doms.keys():
        score = fuzz.token_set_ratio(company_name, i)
        if score >= 50:
            cnt += doms[i]
    try:
        ratio = round(doms[most_probable_domain] / cnt, 4) if cnt != 0 else MIN_RATIO
        if ratio > 1:
            ratio = MIN_RATIO
    except Exception as e:
        logging.error(f"Error calculating ratio: {e}")
        exit()
    result = [company_name, most_probable_domain, cnt, ratio]
    return result

def process_csv(input_csv, output_csv):
    try:
        with open(input_csv, newline='', encoding='utf-8', errors='replace') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            rows = list(reader)
    except Exception as e:
        logging.error(f"Error reading input CSV file: {e}")
        exit()

    results = []
    for row in rows:
        company_name = row[0]
        result = getResults(company_name)
        results.append(row + result[1:])

    try:
        with open(output_csv, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header + ['company_domain', 'similar_domains_count', 'probability'])
            writer.writerows(results)
    except Exception as e:
        logging.error(f"Error writing output CSV file: {e}")
        exit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Find domain names from a list of company names in a CSV file")
    parser.add_argument("input_csv", help="Path to the input CSV file containing company names", type=str)
    parser.add_argument("output_csv", help="Path to the output CSV file to save the results", type=str)
    args = parser.parse_args()
    process_csv(args.input_csv, args.output_csv)
