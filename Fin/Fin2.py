#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun  2 01:43:47 2018

@author: eg
"""

from bs4 import BeautifulSoup
from selenium import webdriver
import logging, time, csv, re, requests
from selenium.webdriver.firefox.options import Options


# Step one START
def extract_all_data(url, url_base=None, limit=None):
    '''
    Takes url as string, url_base as string and limit for bs.find_all
    Returns a list of dictionaries with basic company data

    [
     {'link': 'https://www.conomy.ru/emitent/abrau-durso', 
      'name': ' ПАО «Абрау – Дюрсо»', 
      'ticker': ' ABRD'}, {}, {}
     ]
    '''
    
    s = requests.Session()
    r = s.get(url)

    soup = BeautifulSoup(r.text, 'lxml')
    
    return extract_all_companies(soup, url_base, limit)

def extract_all_companies(soup, url_base=None, limit=None):
    companies = []
    
    table = soup.find(class_='search-results')                   #<div class="search-results">
    time_start = time.time()
    
    for company_data in table.find_all('a', limit=limit):        #<a href="/emitent/unipro">Публичное акционерное общество «Юнипро», ПАО «Юнипро» , UPRO</a>
        company = {}

        company['link'] = url_base + normalizer(company_data['href'])
        string = company_data.get_text()
        company['name'] = find_company_name(string)
        company['ticker'] = find_company_ticker(string)
        
        assert len(company['name']) > 2, '\n\n Strange name\n\n%s' % string
        companies.append(company)
        
    time_spent = round(time.time() - time_start, 2)
    logging.info('Found %s companies in %s seconds', len(companies), time_spent)
    
    return companies
# Step one END

# Helper STAR
def find_company_ticker(string):
    # Below regex works as following:
    # - ?<=\W - matches followwing characters if preceded by \W (word boundary)
    # - [A-Z]{4} - matches [A-Z] four times
    # - ?![A-Z] - matches preceding characters only if not followed by [A-Z]
    try:
        result = normalizer(re.findall('(?<=\W)[A-Z]{4}(?![A-Z])', string)[0])
    except:
        logging.warning('Ticker exception for %s', string)
        result = normalizer(string.split(',')[-1])
    return result       
        
def find_company_name(string):
    # Non-greedy regex .*? matches first match from the beginning
    try:
        result = normalizer(re.findall('«(.*?)»', string)[0])
    except IndexError:
        result = normalizer(string.split(',')[1])
        logging.warning('Company name exception %s selected name %s', string, result)
    return result

def find_table_by_name(table_name, soup):
    table = soup.find_all('table', {'data-name' : re.compile(table_name)})
    assert len(table) <= 1, '\n\nUnique table not found\nTables found:\t%s\nTable name:\t%s' % (len(table), table_name)
    
    if len(table) == 0:
        return None
    else:
        return table[0]
    
def normalizer(string):
    return string.replace('\n', ' ').replace('\xa0', ' ').replace('(рек.)','').strip()

def get_next_tag(tag):
    letter, digit = tag[:1], tag[1:]         # 'A', '7'
    new_tag = chr(ord(letter) + 1) + digit
    return new_tag

def filter_companies_by_ticker(companies, letters):
    result = []
    for company in companies:
        pattern_length = len(letters[0])
        if company['ticker'][:pattern_length] in letters:
            result.append(company)
    
    assert len(result) > 0, 'No companies found for filter %s' % letters
    return result
    
# Helper END

# Step two START
def selenium_get_html(url):
    '''
    Takes url string
    Returns HTML docment (string)
    
    '''
    time_start = time.time()
    assert 'http' in url, '\n\nNo HTTP URL provided\nURL:\t%s' % url
    options = Options()
    options.set_headless(headless=True)    
    driver = webdriver.Firefox(firefox_options=options)
    driver.get(url)

    html = driver.page_source
    driver.close()
    time_spent = round(time.time() - time_start, 2)
    logging.debug('%s processed in %s seconds', url, time_spent)
    return html

def extract_company_data(soup, company, tables):
    '''
    Takes bs4.soup, dict with company data and 
    list of tables and tag values to find
    
    returns dict with company data 
    enriched with new data found
    '''
    for table in tables:
        table_name = table[0]                           # 'общая информация'
        for item in table[1]:                           # ('A7', 'B7')
            xml_table = find_table_by_name(table_name, soup)
            
            if xml_table == None:                       # Таблица не найдена
                continue
            
            key_tag = item[0]
            value_tag = item[1]
            
            #print(item, key_tag, value_tag)
            company_property_key = xml_table.find('td', 
                                                  {'data-id' : key_tag}).get_text() # Отрасль
            company_property_value = xml_table.find('td', 
                                                    {'data-id' : value_tag}).get_text() # Чёрная металлургия

            company_property_value = normalizer(company_property_value)
            company_property_key = normalizer(company_property_key)
            company[company_property_key] = company_property_value

    return company

def extract_company_data_by_text(soup, company, tables):
    '''
    Takes bs4.soup, dict with company data and 
    list of tables and text values to find
    
    returns dict with company data 
    enriched with new data found
    '''
    for table in tables:
        table_name = table[0]                           # 'общая информация'
        xml_table = find_table_by_name(table_name, soup)
        for item in table[1]:                           # 'EBITDA, тыс. руб.'
            
            if xml_table == None:                       # Таблица не найдена
                continue
                        
            try:
                found_elem_tag = xml_table.find('td', string=item)['data-id']    # 'A7'
                next_tag = get_next_tag(found_elem_tag)
                company_property_value = xml_table.find('td',
                                                        { 'data-id' : next_tag }).get_text()
                company_property_value = normalizer(company_property_value)
                
            except TypeError:
                company_property_value = ''
                
            company_property_key = item
            company[company_property_key] = company_property_value
            
            #print(company_property_key, company_property_value)
            '''
            if 'Текущая цена' in item:
                print(table_name, item, found_elem_tag, next_tag, company_property_value)
                print(xml_table.find('td', string=item))
                print(soup.find('td', { 'data-id' : next_tag }))
                print(xml_table)
            '''

    return company


def enrich_all_data(data, url_base):
    '''
    Takes a url_base string and 
    a list of dictionaries with company data like:
    
    [{'link': 'https://www.conomy.ru/emitent/uralkalij', 
                  'name': ' ПАО «Уралкалий»', 'ticker': ' URKA'},
            {'link': 'https://www.conomy.ru/emitent/uralkuz',
             'name': ' ПАО «Уралкуз» ', 'ticker': ' URKZ'}
            ]
    
    Returns list with each company data enriched with new table data
    '''
    
    # Here goes series of tables each with:
    # - A part of table name (HTML element will be found by)
    # - A list of HTML text values to find elements

    general_info = [
            ('общая информация', ['Отрасль',
                                  'Вид деятельности',
                                  'Статус'])
            ]
    koefficienti_variant_1 = [
            ('коэффициенты', ['Текущая цена, руб.',
                              'Потенциал, %'])
            ]
            
    koefficienti_variant_2 = [
            ('- потенциал', ['Текущая цена, руб.',
                             'Потенциал, %'])
            ]

    kotirovki = [('котировки', [('A4', 'E4'),('F1', 'F2')])]
            
    akcii = [('акции',[('G1', 'G2')])]
    
    tables_from_main_page_by_tag = [kotirovki, akcii]
    
    tables_from_main_page_by_text = [general_info, koefficienti_variant_1, koefficienti_variant_2]
    
    tables_multiplicators_text_page = [
            ('Рыночные коэффициенты', ['EBITDA, тыс. руб.',
                                       'EBITDA (прогноз), тыс. руб.',
                                       'Book Value, тыс. руб.',
                                       'EV, тыс. руб.',
                                       'EV/EBITDA',
                                       'EV/EBITDA по прогнозным\nпоказателям',
                                       'Чистый долг/EBITDA',
                                       'Прибыль на акцию, руб',
                                       'P/E',
                                       'P/E по прогнозным\nпоказателям',
                                       'PEG',
                                       'P/S',
                                       'P/S по прогнозным\nпоказателям',
                                       'P/BV',
                                       'EV/S',
                                       'EV/S по прогнозным\nпоказателям',
                                       'Дивидендная доходность (АОИ), %',
                                       'Дивидендная доходность (АПИ), %'
                                       ])
    ]

    for company in data:
        logging.debug('Ticker:\t%s', company['ticker'])
        time_start = time.time()
        url = company['link']
        
        soup = BeautifulSoup(selenium_get_html(url), 'lxml')
        
        # First enrich with data from main company page
        for table in tables_from_main_page_by_tag:
            company = extract_company_data(soup, company, table)
            
        for table in tables_from_main_page_by_text:
            company = extract_company_data_by_text(soup, company, table)
        
        # On the main company page Find URLs to interesting data
        extra_pages = get_extra_pages(soup, url_base)
        
        for page in extra_pages.keys():
            url = extra_pages[page]
            
            if url != '':
            
                soup = BeautifulSoup(selenium_get_html(extra_pages[page]), 'lxml')
                company = extract_company_data_by_text(soup, company, tables_multiplicators_text_page)
        time_spent = round(time.time() - time_start, 2)

        logging.info('[%s of %s] %s processed in %s seconds',
                     data.index(company)+1, len(data), company['name'], time_spent)
    return data
        
# Step two END  
    
# Step three START
def get_extra_pages(soup, url_base):
    '''
    Takes bs4.soup and url_base
    Returns a dict with urls for extra data:
        
    {'Дивиденды': 'https://www.conomy.ru/emitent/uralkalij/urka-div', 
    'Рыночные коэффициенты': 'https://www.conomy.ru/emitent/uralkalij/urka-rk'}
    
    
    extra_pages = { 'Дивиденды' : '', 
                     'Рыночные коэффициенты' : ''
                     }
    '''
    extra_pages = { 'Рыночные коэффициенты' : '' }
    for page in extra_pages.keys():
        try:
            url = url_base + soup.find('span', string=page).parent['href']
        except AttributeError:
            url = ''

        extra_pages[page] = url
            
    return extra_pages
# Step three END
    
def write_company_data_to_csv(companies):
    # Something WRON in CSV writer
    
    header = [
            'link',
            'name',
            'ticker',
            'Рыночная капитализация, тыс. руб.',
            'Объем торгов, руб.',
            'Уровень листинга', 
            'Отрасль', 
            'Вид деятельности', 
            'Статус', 
            'Текущая цена, руб.',
            'Потенциал, %', 
            'EBITDA, тыс. руб.'
            'EBITDA (прогноз), тыс. руб.'
            'Book Value, тыс. руб.', 
            'EV, тыс. руб.', 
            'EV/EBITDA',
            'EBITDA по прогнозным\nпоказателям', 
            'Чистый долг/EBITDA', 
            'Прибыль на акцию, руб', 
            'P/E', 
            'P/E по прогнозным\nпоказателям', 
            'PEG',
            'P/S',
            'P/S по прогнозным\nпоказателям',
            'P/BV',
            'EV/S',
            'EV/S по прогнозным\nпоказателям',
            'Дивидендная доходность (АОИ), %',
            'Дивидендная доходность (АПИ), %'
            ]
    with open('results_copmanies.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, extrasaction='ignore', 
                          fieldnames=header)
        writer.writeheader()
        for company in companies:
            writer.writerow(company)
    

def find_all_data():
    time_start = time.time()
    logging.basicConfig(
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.INFO,
            datefmt='%H:%M:%S')
    
    limit = 150
    ticker_letters = ['NAUK']
    url_base = 'https://www.conomy.ru'
    url_search = 'https://www.conomy.ru/search'
    

    companies = [{'link': 'https://www.conomy.ru/emitent/nauka', 
                  'name': '«Наука»', 'ticker': 'NAUK'},
            ]
    
    
    #companies = extract_all_data(url_search, url_base, limit)
    #companies = filter_companies_by_ticker(companies, ticker_letters)
    companies = enrich_all_data(companies, url_base)
    time.sleep(1)
    time_spent = round(time.time() - time_start, 2)
    logging.info('Finished processing of %s companies in %s seconds',
                 len(companies), time_spent)

    write_company_data_to_csv(companies)

find_all_data()
