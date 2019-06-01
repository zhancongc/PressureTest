import re
import pymongo


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


if __name__ == "__main__":
    zebra = ZebraOffline()
    zebra.calculate_pdf_size()

