# -*- coding: utf-8 -*-

import HTMLParser
from math import ceil
from time import sleep
import urllib2
import sys
from BeautifulSoup import BeautifulSoup


URL = 'https://clinicaltrials.gov/ct2/results?term=&recr=Recruiting&rslt=&type=Intr&cond=cancer&intr=&titles=&outc=&spons=&lead=&id=&state1=&cntry1=NA%3AMX&state2=&cntry2=&state3=&cntry3=&locn=&gndr=&rcv_s=&rcv_e=&lup_s=&lup_e='
COUNTRY = 'Mexico'
DELAY = 1


entities = HTMLParser.HTMLParser()


def urlread(url):
    code = False
    html = False
    try:
        response = urllib2.urlopen(url)
        html = response.read()
        code = response.code
    except urllib2.HTTPError, err:
        if err.getcode() == 404:
            code = err.getcode()
            html = None
        else:
            raise
    return code, html


def get_num_results(soup):
    summary = soup.find('div', {'class': 'results-summary'})
    num_results = int(summary.strong.getText().split()[0])
    return num_results


def get_num_pages(num_results):
    num_pages = int(ceil(float(num_results)/20))
    return num_pages


def get_page_results(soup):
    parsed = []
    res_div = soup.find('div', {'class': 'indent1 header3'})
    results = res_div.findAll('tr', {'style': 'vertical-align:top'})
    for i in range(1, len(results)+1):
        if i % 3 == 0:
            children = results[i-3].findChildren(recursive=False)
            res_dict = {}
            for x in range(len(children)):
                if x == 0:
                    rank = children[x].getText()
                    res_dict['rank'] = rank
                elif x == 1:
                    status = children[x].getText()
                    res_dict['status'] = status
                elif x == 2:
                    study_children = children[x].findChildren()
                    res_dict['id'] = \
                        study_children[0].attrs[1][1].split('/')[-1].split('?')[0]
            parsed.append(res_dict)
    return parsed


def get_study(study_url):
    study = {}
    sleep(DELAY)
    code, html = urlread(study_url)
    if code != 200:
        sys.exit('HTTP return code not 200. Quitting.')
    elif html is None:
        sys.exit('HTTP request returned an empty html')
    else:
        soup = BeautifulSoup(html)
        content = soup.find('div', {'id': 'main-content'})
        title = content.find('h1', {'class': 'solo_record'})
        study['title'] = entities.unescape(title.getText())
        sponsor = content.find('div', {'id': 'sponsor'})
        study['sponsor'] = entities.unescape(sponsor.getText())
        purpose = content.find('div', {'class': 'body3'})
        purpose_children = purpose.findChildren(recursive=False)
        purpose_lines = []
        for child in purpose_children:
            if child.name.lower() == 'p':
                paragraph = '\t' + child.getText().strip()
                purpose_lines.append(paragraph)
            if child.name.lower() == 'ul':
                for list_item in child.findChildren(recursive=False):
                    # Next 3 lines probably unecessary. Left just in case list
                    # has children that are not 'li'.
                    if list_item.name.lower() != 'li':
                        print 'List has a children that is not \'li\'.'
                        raw_input('press ENTER to continue...')
                    list_item_str = '\t  - ' + list_item.getText()
                    purpose_lines.append(list_item_str)
        purpose_string = '\n'.join(purpose_lines)
        study['purpose'] = entities.unescape(purpose_string)
        purpose_table = content.find('table', {'class': 'data_table'})
        cols = purpose_table.findAll('td', {'class': 'body3'})
        conditions = [l for l in cols[0].prettify().split('\n')
                      if not l.startswith('<') and l]
        conditions = [entities.unescape(c) for c in conditions]
        study['conditions'] = conditions
        try:
            interventions = [l for l in cols[1].prettify().split('\n')
                             if not l.startswith('<') and l]
            interventions = [entities.unescape(l) for l in interventions]
            interventions.sort()
            study['interventions'] = interventions
        except IndexError:
            study['interventions'] = ''
        loc_table = content.find(
            'table', {'class': 'layout_table indent2',
                      'summary': 'Layout table for location information'})
        loc_items = loc_table.findAll('tr')
        found_target = False
        locations = []
        for tr_i in range(len(loc_items)):
            country_td = loc_items[tr_i].find('td',
                                              {'class': 'header3',
                                               'style': 'padding-top:2ex'})
            if country_td:
                if country_td.getText() != COUNTRY:
                    found_target = False
            if found_target is True:
                name_td = loc_items[tr_i].find('td', {'headers': 'locName'})
                if name_td:
                    loc_name = \
                        loc_items[tr_i].find(
                            'td', {'headers': 'locName'}).getText()
                    loc_status = \
                        loc_items[tr_i].find(
                            'td', {'headers': 'locStatus'}).getText()
                    loc_place = loc_items[tr_i+1].getText()
                    loc_str = ''
                    if loc_status:
                        loc_str += '[' + loc_status.upper() + '] '
                    if loc_name:
                        loc_str += loc_name + '; '
                    loc_str += loc_place
                    loc_str = entities.unescape(loc_str)
                    locations.append(loc_str)
            if country_td:
                if country_td.getText() == COUNTRY:
                    found_target = True
        study['locations'] = locations
    return study


def search_ct(search_url):
    results = []
    code, html = urlread(search_url)
    if code != 200:
        sys.exit('HTTP return code not 200. Quitting.')
    elif html is None:
        sys.exit('HTTP request returned an empty html.')
    else:
        soup = BeautifulSoup(html)
        num_res = get_num_results(soup)
        num_pgs = get_num_pages(num_res)
        firstpg = get_page_results(soup)
        results += firstpg
        for i in range(2, num_pgs+1):
            sleep(DELAY)
            next_page_url = search_url + '&pg=' + str(i)
            code, html = urlread(next_page_url)
            if code != 200:
                sys.exit('HTTP return code not 200. Quitting.')
            elif html is None:
                sys.exit('HTTP request returned an empty html.')
            else:
                soup = BeautifulSoup(html)
                pg = get_page_results(soup)
                results += pg
    return results


def main(url):
    search_results = search_ct(url)
    print 'SEARCH URL:', url
    print '%s RESULTS FOUND.' % len(search_results)
    print '=' * 79
    for r in search_results:
        print
        print 'RANK:', r['rank']
        print 'ID:', r['id']
        study_url = 'https://clinicaltrials.gov/ct2/show/' + r['id']
        print 'URL:', study_url
        study = get_study(study_url + '?show_locs=Y#locn')
        print 'TITLE:', study['title'].encode('utf-8')
        print 'SPONSOR:', study['sponsor'].encode('utf-8')
        print 'PURPOSE:'
        print study['purpose'].encode('utf-8')
        if len(study['conditions']) == 0:
            print 'CONDITIONS: None listed.'
        else:
            print 'CONDITIONS:'
            for c in study['conditions']:
                print '\t' + c.encode('utf-8')
        if len(study['interventions']) == 0:
            print 'INTERVENTIONS: None listed.'
        else:
            print 'INTERVENTIONS:'
            for i in study['interventions']:
                print '\t' + i.encode('utf-8')
        if len(study['locations']) == 0:
            print 'LOCATIONS: None listed.'
        else:
            print 'LOCATIONS:'
            for l in study['locations']:
                print '\t' + l.encode('utf-8')
        #raw_input('===[ Press ENTER to continue ]===')


if __name__ == '__main__':
    main(URL)
