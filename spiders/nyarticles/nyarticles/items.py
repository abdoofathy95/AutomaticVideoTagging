import scrapy


class NyarticlesItem(scrapy.Item):
	tags = scrapy.Field()
	title = scrapy.Field()
	article = scrapy.Field()