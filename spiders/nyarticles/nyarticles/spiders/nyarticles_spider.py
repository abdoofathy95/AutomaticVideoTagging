from scrapy.selector import Selector
from scrapy.spiders import CrawlSpider ,Rule
from nyarticles.items import NyarticlesItem
from scrapy.linkextractors import LinkExtractor
import re


match_website = re.compile(r'[\/+[0-9]+\/[0-9]+\/[0-9]+\/.*]')

class NyarticlesSpider(CrawlSpider):

	name = "NyarticlesSpider"
	allowed_domains = ["nytimes.com"]
	start_urls = ["http://www.nytimes.com/"] # end date = 08/03/2016 in YYYYMMDD

	rules = (
        Rule(LinkExtractor(allow=()), callback='parse_article',follow=True),
     )

	def parse_article(self,response):
		item = NyarticlesItem()
		keywords = response.xpath("//meta[@name='keywords']/@content").extract()
		if len(keywords) > 0:
			item['tags'] = keywords[0]
		item['title'] = response.selector.xpath('//title/text()').extract()[0].encode('ascii','ignore')
		item['article'] = response.selector.xpath("//p[@class='story-body-text' or @itemprop='articleBody' or @class='story-body-text story-content' or @class='Textbody']/text()").extract()
		return item

	# response.xpath("//meta[@name='keywords']/@content").extract()[0].split(',')
	# response.selector.xpath('//title/text()').extract()[0].encode('ascii','ignore')
	# response.selector.xpath("//p[@class='story-body-text story-content']/text()").extract()
	# data = data['response']['docs']
