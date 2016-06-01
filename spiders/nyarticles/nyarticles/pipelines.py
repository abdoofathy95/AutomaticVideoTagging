# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import psycopg2

class NyarticlesPipeline(object):

	def __init__(self):
		self.conn = psycopg2.connect("dbname=nyarticles user=abdoo")
		self.cursor = self.conn.cursor()

	def process_item(self, item, spider):

		if len(item['article']) > 0 and len(item['tags']) > 0 and len(item['title']) > 0:
			article = " ".join(item['article'])
			article = (article.encode('ascii','ignore')).strip()
			tags = "".join(item['tags']).split(',')
			query = "INSERT INTO articles(title,articletext) VALUES (%s,%s) RETURNING id;"
			data = (item['title'],article)
			query2 = "INSERT INTO tags(article_id,tag) VALUES (%s,%s);"
			self.cursor.execute(query,data)
			article_id = str(self.cursor.fetchone()[0])
			for tag in tags:
				data2 = (article_id,tag)
				self.cursor.execute(query2,data2)
				if len(article) > 5:
					self.conn.commit()
		return item

	def close_spider(self, spider):
		self.conn.close()