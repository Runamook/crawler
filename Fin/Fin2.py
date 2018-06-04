#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun  2 01:43:47 2018

@author: eg
"""

from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import re
import csv
import logging
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
    
    table = soup.find(class_='search-results')      #<div class="search-results">
    
    for company_data in table.find_all('a', limit=limit):        #<a href="/emitent/unipro">Публичное акционерное общество «Юнипро», ПАО «Юнипро» , UPRO</a>
        company = {}
        company['link'] = url_base + normalizer(company_data['href'])
        string = normalizer(company_data.get_text()).split(',')
        company['name'] = string[1]
        company['ticker'] = string[2]

        companies.append(company)
        
    return companies
# Step one END

# Helper STAR
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
# Helper END

# Step two START
def selenium_get_html(url):
    '''
    Takes url string
    Returns HTML docment (string)
    
    '''
    assert 'http' in url, '\n\nNo HTTP URL provided\nURL:\t%s' % url
    options = Options()
    options.set_headless(headless=True)    
    driver = webdriver.Firefox(firefox_options=options)
    driver.get(url)

    html = driver.page_source
    driver.close()
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
            company_property_key = xml_table.find('td', {'data-id' : key_tag}).get_text() # Отрасль
            company_property_value = xml_table.find('td', {'data-id' : value_tag}).get_text() # Чёрная металлургия

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
        for item in table[1]:                           # 'EBITDA, тыс. руб.'
            xml_table = find_table_by_name(table_name, soup)
            
            if xml_table == None:                       # Таблица не найдена
                continue
                        
            #print(company['name'], key_text)
            try:
                found_elem_tag = xml_table.find('td', string=item)['data-id']    # 'A7'
                next_tag = get_next_tag(found_elem_tag)
                company_property_value = soup.find('td', { 'data-id' : next_tag }).get_text()
                company_property_value = normalizer(company_property_value)
                
            except TypeError:
                company_property_value = ''
                
            company_property_key = item
            company[company_property_key] = company_property_value

            '''
            if 'EV/EBITDA' in item or 'DA по прогноз' in item:
                print(item, found_elem_tag, next_tag, company_property_value)
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
    # - A list of HTML tag values (key value) to grab

    tables_from_main_page = [
            ('общая информация', [('A7', 'B7'),
                                  ('A8', 'B8'), 
                                  ('A9','B9')]),
    ('котировки', [('A4', 'E4'),
                   ('F1', 'F2')]),
    ('акции',[('G1', 'G2')]),
    ('коэффициенты',[('A2', 'C2'),
                     ('A3', 'C3'),
                     ('A4', 'C4'),
                     ('B8', 'C8')])
    ]
        
    '''
    tables_dividend_page = [
            ('дивиденды', [('A3', 'F3'),
                           ('A4', 'F4'),
                           ('A5', 'F5')]),
    ('дивидендная доходность', [('A3', 'E3'),
                                ('A4', 'E4'),
                                ('A5', 'E5')])
    ]
    '''
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
        url = company['link']
        
        #logging.debug(company, url)
        soup = BeautifulSoup(selenium_get_html(url), 'lxml')
        
        # First enrich with data from main company page
        for table in tables_from_main_page_by_tag:
            company = extract_company_data(soup, company, table)
            
        for table in tables_from_main_page_by_text:
            company = extract_company_data_by_text(soup, company, table)
        
        # On the main company page Find URLs to interesting data
        extra_pages = get_extra_pages(soup, url_base)
        
        for page in extra_pages.keys():
            #try:
            soup = BeautifulSoup(selenium_get_html(extra_pages[page]), 'lxml')
            if page == 'Дивиденды':
                pass
                #company = extract_company_data(soup, company, tables_dividend_page)
            elif page == 'Рыночные коэффициенты' and extra_pages[page] != '':
                company = extract_company_data_by_text(soup, company, tables_multiplicators_text_page)
        
    return data
        
# Step two END  
    
# Step three START
def get_extra_pages(soup, url_base):
    '''
    Takes bs4.soup and url_base
    Returns a dict with urls for extra data:
        
    {'Дивиденды': 'https://www.conomy.ru/emitent/uralkalij/urka-div', 
    'Рыночные коэффициенты': 'https://www.conomy.ru/emitent/uralkalij/urka-rk'}
    
    '''
    extra_pages = { 'Дивиденды' : '', 
                     'Рыночные коэффициенты' : ''
                     }
    for page in extra_pages.keys():
        try:
            url = url_base + soup.find('span', string=page).parent['href']
        except AttributeError:
            url = ''

        extra_pages[page] = url
            
    return extra_pages
# Step three END
    
def write_company_data_to_csv(companies):
	with open('results_copmanies.csv', 'w') as csvfile:
		fieldnames = companies[0].keys()
		writer = csv.DictWriter(csvfile, extrasaction='ignore', fieldnames=fieldnames)
		writer.writeheader()
		for company in companies:
			writer.writerow(company)
				 


def find_all_data():
    
    logging.basicConfig(level=logging.INFO)
    limit = 15
    url_base = 'https://www.conomy.ru'
    url_search = 'https://www.conomy.ru/search'
    
    companies = [{'link': 'https://www.conomy.ru/emitent/uralkalij', 
                  'name': ' ПАО «Уралкалий»', 'ticker': ' URKA'},
            {'link': 'https://www.conomy.ru/emitent/uralkuz',
             'name': ' ПАО «Уралкуз» ', 'ticker': ' URKZ'}
            ]
    
    companies = extract_all_data(url_search, url_base, limit)
    companies = enrich_all_data(companies, url_base)
    
    write_company_data_to_csv(companies)
    print(companies)
    '''
    for company in companies:
        for key in company.keys():
            print(key, company[key], sep='\t\t')
            
        print('\n')     
    '''      
find_all_data()