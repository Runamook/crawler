# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup

def get_html(url):
    r = requests.get(url)   # Response
    return r.text           # returns HTML-code

def get_all_links(html):
    soup = BeautifulSoup(html, 'lxml')
    
    a_s = soup.find_all('a')
    links = []
    
    for a in a_s:
        i = a.get('href')
        if 'http' in i:
            links.append(i)
        
    return links

def main():
    url = 'http://dividendo.ru/dividendnye-istorii-kompaniy.html'
    
    all_links = get_all_links(get_html(url))
    
    for link in all_links:
        print(link)

if __name__ == '__main__':
    main()
    
