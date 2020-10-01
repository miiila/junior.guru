import html

import arrow
from scrapy import Spider as BaseSpider
from scrapy.loader import ItemLoader
from itemloaders.processors import Compose, Identity, MapCompose, TakeFirst

from juniorguru.scrapers.items import Job


class Spider(BaseSpider):
    name = 'startupjobs'
    start_urls = [
        'https://feedback.startupjobs.cz/feed/juniorguru.php'
    ]

    def parse(self, response):
        for n, offer in enumerate(response.xpath('//offer'), start=1):
            for city in offer.xpath('.//city/text()').getall():
                loader = Loader(item=Job(), response=response)
                offer_loader = loader.nested_xpath(f'//offer[{n}]')
                offer_loader.add_xpath('title', './/position/text()')
                offer_loader.add_xpath('link', './/url/text()')
                offer_loader.add_xpath('company_name', './/startup/text()')
                offer_loader.add_xpath('company_link', './/startupURL/text()')
                offer_loader.add_value('location_raw', city)
                offer_loader.add_xpath('remote', ".//jobtype[contains(., 'Remote')]/text()")
                offer_loader.add_value('remote', False)
                offer_loader.add_xpath('employment_types', './/jobtype/text()')
                offer_loader.add_xpath('posted_at', './/lastUpdate//text()')
                offer_loader.add_xpath('description_html', './/description/text()')
                offer_loader.add_xpath('company_logo_urls', './/startupLogo/text()')
                yield loader.load_item()


def drop_remote(types):
    return [type_ for type_ in types if type_.lower() != 'remote']


def parse_iso_date(value):
    return arrow.get(value).date()


class Loader(ItemLoader):
    default_input_processor = MapCompose(str.strip)
    default_output_processor = TakeFirst()
    title_in = MapCompose(html.unescape)
    company_name_in = MapCompose(html.unescape)
    employment_types_in = Compose(MapCompose(str.strip), drop_remote)
    employment_types_out = Identity()
    posted_at_in = MapCompose(parse_iso_date)
    company_logo_urls_out = Identity()
    remote_in = MapCompose(bool)
