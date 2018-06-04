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
        if 'http' in i and 'php?' not in i and len(i) > 22 :
            links.append(i.replace(' ','').strip())
            
    return links

def get_page_data(html,link):
    soup = BeautifulSoup(html, 'lxml')
    
    try:
        #name = soup.find('span', itemprop='title').text
        name = soup.find('a', href=link).find('span').text.strip()
    except:
        name = ''
        
    try:
        div = soup.find('tbody').find('td').text
    except:
        div = ''
        
    data = {'name' : name,
            'div' : div}
    return data
    
    
    
def main():
    url = 'http://dividendo.ru/dividendnye-istorii-kompaniy.html'
    
    all_links = get_all_links(get_html(url))
    
    for link in all_links:
        #data = get_page_data(get_html(link), link)
        #print(link, data)
        print(link)

if __name__ == '__main__':
    main()
    
