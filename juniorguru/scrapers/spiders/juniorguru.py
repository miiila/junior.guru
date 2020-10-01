import re
import hashlib
from urllib.parse import urlparse

from scrapy import Spider as BaseSpider

from juniorguru.lib import google_sheets
from juniorguru.lib.md import md
from juniorguru.lib.coerce import (coerce, parse_datetime, parse_text,
    parse_date, parse_set, parse_boolean_words)
from juniorguru.scrapers.items import JuniorGuruJob
from juniorguru.scrapers.settings import JUNIORGURU_ITEM_PIPELINES


class Spider(BaseSpider):
    name = 'juniorguru'
    custom_settings = {'ITEM_PIPELINES': JUNIORGURU_ITEM_PIPELINES}
    doc_key = '1TO5Yzk0-4V_RzRK5Jr9I_pF5knZsEZrNn2HKTXrHgls'
    sheet_name = 'jobs'
    override_response_url = f'https://docs.google.com/spreadsheets/d/{doc_key}/edit#gid=0'
    override_response_backup_path = None

    # https://stackoverflow.com/q/57060667/325365
    # https://developers.google.com/sheets/api/reference/rest#discovery-document
    start_urls = ['https://sheets.googleapis.com/$discovery/rest?version=v4']

    def _get_records(self):
        sheet = google_sheets.get(self.doc_key, self.sheet_name)
        return google_sheets.download(sheet)

    def parse(self, response):
        for record in self._get_records():
            data = coerce_record(record)
            for data_per_location in split_multiple_locations(data):
                yield JuniorGuruJob(**data_per_location)


def coerce_record(record):
    job = coerce({
        r'^timestamp$': ('posted_at', parse_datetime),
        r'^company name$': ('company_name', parse_text),
        r'^employment type$': ('employment_types', parse_set),
        r'^job title$': ('title', parse_text),
        r'^company website link$': ('company_link', parse_text),
        r'^email address$': ('email', parse_text),
        r'remote': ('remote', parse_boolean_words),
        r'location': ('location_raw', parse_text),
        r'^job description$': ('description_html', parse_markdown),
        r'^job link$': ('link', parse_text),
        r'^pricing plan$': ('pricing_plan', parse_pricing_plan),
        r'^approved$': ('approved_at', parse_date),
        r'^expire[ds]$': ('expires_at', parse_date),
    }, record)
    job['id'] = create_id(job['posted_at'], job['company_link'])
    return job


def split_multiple_locations(data):
    location = data.get('location_raw')
    if location:
        for sub_location in re.split(r'\snebo\s', location):
            yield {**data, 'location_raw': sub_location.strip()}
    else:
        yield data


def parse_markdown(value):
    if value:
        return md(value.strip())


def parse_pricing_plan(value):
    if value:
        value = value.strip().lower()
        if 'flat rate' in value:
            return 'annual_flat_rate'
        if not value.startswith('0 czk'):
            return 'standard'
    return 'community'


def create_id(posted_at, company_link):
    url_parts = urlparse(company_link)
    seed = f'{posted_at:%Y-%m-%dT%H:%M:%S} {url_parts.netloc}'
    return hashlib.sha224(seed.encode()).hexdigest()
