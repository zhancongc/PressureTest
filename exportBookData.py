import re
import os
import pymongo
import requests


class ZebraOffline(object):
    def __init__(self):
        self.db = self.connect_db()

    @staticmethod
    def connect_db():
        """
        :return db: object
        """
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["itbooks"]
        return db

    def calculate_pdf_size(self):
        # r'(\d)+\.?(\d+)?'
        out = self.db['books'].find({}, {"_id": 0, "File size": 1, "Book link": 1})
        pdf_total_size = 0
        for i in out:
            temp = re.match(r'(\d)+\.?(\d+)?', i["File size"])
            if temp:
                size = eval(temp.group())
                pdf_total_size += size
        print(pdf_total_size)

    def download_book_thumbnail(self):
        print(os.path.curdir)
        out = self.db['books'].find({}, {"_id": 0, "Thumbnail": 1})
        for i in out:
            if i:
                print(i)
                thumbnail_name = i['Thumbnail'].split('/')[-1]
                try:
                    r = requests.get(url=i['Thumbnail'])
                    fp = open('./Thumbnail/' + thumbnail_name, 'wb')
                    fp.write(r.content)
                    fp.close()
                except Exception as e:
                    print(e)


if __name__ == "__main__":
    zebra = ZebraOffline()
    zebra.download_book_thumbnail()

