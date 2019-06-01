import unittest
import threading
import requests
import random
import pymongo
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
        self.headers = [{
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "br, gzip, deflate",
            "Accept-Language": "zh-cn",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0.3 Safari/605.1.15"
        }, {
            "Accept": "text/html, application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Encoding": "gzip, deflate,brAccept-Language: en-US;q=0.9",
            "Cache - Control": "max-age=0",
            "Connection": "keep-alive",
            "Accept-Language": "en-US",
            "User-Agent": "Mozilla / 5.0(iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML,like Gecko) Version/11.0 Mobile/15A372 Safari / 604.1"
        }]
        self.db = self.connect_db()
        self.book_urls = self.get_book_urls_online()

    def get_book_data(self, book_url):
        """
        :param book_url:  str
        :return book:  dict
        """
        print("start get book urls: %s" % book_url)
        if self.db.books.find_one({'Book link': book_url}):
            print('[ERROR] mongo has this book. book url: %s' % book_url)
            return None
        try:
            client = requests.get(book_url, headers=random.choice(self.headers))
        except Exception as e:
            print('[ERROR] cannot connect to server, please retry: %s' % book_url)
            print(e)
            return None
        soup = BeautifulSoup(client.text, 'lxml')
        book = dict()
        try:
            download_link = soup.find(name='span', attrs={'class': 'download-links'}).a.get('href').replace(' ', '%20')
            book_name = soup.find(name='h1', attrs={'class': 'single-title'}).text.strip()
            book_image_node = soup.find(name='img', attrs={'alt': book_name}) or soup.find(name='img', attrs={'class': 'wp-post-image'})
            book_image = book_image_node.get('src')
            book_description = soup.find(name='div', attrs={'class': 'entry-content'}).text.strip()
            book.update({
                "Book link": book_url,
                "Download link": download_link,
                "Name": book_name,
                "Thumbnail": book_image,
                "Description": book_description
            })
            book_detail = soup.find(name='div', attrs={'class': 'book-detail'})
            book_detail_list = []
            for i in book_detail.findAll('dt'):
                book_detail_list.append(i.text.strip().replace(":", ''))
            for j in book_detail.findAll('dd'):
                book_detail_list.append(j.text.strip())
            book.update(self.deal(book_detail_list))
            self.db.books.insert_one(book)
        except Exception as e:
            print(e)
            print('[ERROR] data parsing error, please retry: %s' % book_url)
            return None
        print(book)

    @staticmethod
    def deal(array):
        out = dict()
        left, right = 0, len(array)//2
        while right < len(array):
            out.update({array[left]: array[right]})
            right += 1
            left += 1
        return out

    def get_book_urls_online(self):
        """
        :return None:
        """
        print("start get book urls")
        book_urls = list()
        # max = 819
        for page_num in range(100, 819):
            page_url = self.base_url + 'page/' + str(page_num) + '/'
            client = requests.get(page_url, headers=random.choice(self.headers))
            soup = BeautifulSoup(client.text, 'lxml')
            book_url_list = soup.findAll(name="a", attrs={"rel": "bookmark"})
            for book_url_tag in book_url_list:
                temp_url = book_url_tag.get("href")
                if temp_url not in book_urls:
                    book_urls.append(temp_url)
                    print(book_url_tag.get("href"))
                    self.db['booklink'].insert_one({'Book link': book_url_tag.get("href")})
        print("finish get book urls")
        return book_urls

    def run(self):
        threads = list()
        print(self.book_urls)
        for url in self.book_urls:
            th = threading.Thread(target=self.get_book_data(book_url=url))
            threads.append(th)
        for th in threads:
            th.start()
        for th in threads:
            th.join()

    @staticmethod
    def connect_db():
        """
        :return db: object
        """
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["itbooks"]
        return db


if __name__ == "__main__":
    zebra = Zebra()
    zebra.run()








