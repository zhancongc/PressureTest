import unittest
import requests
import random
from bs4 import BeautifulSoup
'''
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument('--headless')
base_url = "http://www.allitebooks.org/"
browser = webdriver.Chrome(options=chrome_options,
                           executable_path="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chromedriver.exe")
book_url = "make-your-own-twine-games/"
browser.get(base_url+book_url)
print(browser.page_source)
soup = BeautifulSoup(browser.page_source, 'lxml')
node = soup.find(name='span', attrs={'class': 'download-links'})
download_url = node.a.get('href')
browser.close()
browser.quit()
'''


class Zebra(object):
    def __init__(self):
        self.base_url = "http://www.allitebooks.org/"
        self.headers = [
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "br, gzip, deflate",
            "Accept-Language": "zh-cn",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0.3 Safari/605.1.15"
        },
        {
            "Accept": "text/html, application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Encoding": "gzip, deflate,brAccept-Language: en-US;q=0.9",
            "Cache - Control": "max-age=0",
            "Connection": "keep-alive",
            "Accept-Language": "en-US",
            "User-Agent": "Mozilla / 5.0(iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML,like Gecko) Version/11.0 Mobile/15A372 Safari / 604.1"
        }
        ]

    def get_book_url(self, book_url):
        """
        :param book_url:  str
        :return book:  dict
        """
        client = requests.get(url=self.base_url+book_url, headers=random.choice(self.headers))
        soup = BeautifulSoup(client.text, 'lxml')
        book = dict()
        download_link = soup.find(name='span', attrs={'class': 'download-links'}).a.get('href').replace(' ', '%20')
        book_name = soup.find(name='h1', attrs={'class': 'single-title'}).text.strip()
        book_image = soup.find(name='img', attrs={'alt': book_name}).get('src')
        book_description = soup.find(name='div', attrs={'class': 'entry-content'}).text.strip()
        book.update({"Download link": download_link, "Name": book_name, "Thumbnail": book_image, "Description": book_description})

        book_detail = soup.find(name='div', attrs={'class': 'book-detail'})
        book_detail_list = []
        for i in book_detail.findAll('dt'):
            book_detail_list.append(i.text.strip())
        for j in book_detail.findAll('dd'):
            book_detail_list.append(j.text.strip())
        book.update(self.deal(book_detail_list))
        return book

    @staticmethod
    def deal(array):
        out = dict()
        left, right = 0, len(array)//2
        while right < len(array):
            print(array[left], array[right])
            out.update({array[left]: array[right]})
            right += 1
            left += 1
        return out

    def get_book_url(self):
        pass


if __name__ == "__main__":
    zebra = Zebra()
    print(zebra.get_book_url("make-your-own-twine-games/"))







