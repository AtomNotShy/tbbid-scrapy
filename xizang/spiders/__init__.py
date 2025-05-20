# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.
from scrapy.cmdline import execute

if __name__ == '__main__':

    execute('scrapy crawl employee_list'.split())