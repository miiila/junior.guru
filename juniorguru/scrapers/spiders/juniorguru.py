import re
import hashlib
from urllib.parse import urlparse

from scrapy import Spider as BaseSpider

from juniorguru.lib import google_sheets
from juniorguru.lib.coerce import (coerce, parse_datetime, parse_text,
    parse_date, parse_set, parse_boolean_words)
from juniorguru.scrapers.items import JuniorGuruJob, parse_markdown
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
            yield JuniorGuruJob(**coerce_record(record))


def coerce_record(record):
    data = coerce({
        r'^timestamp$': ('posted_at', parse_datetime),
        r'^název firmy$': ('company_name', parse_text),
        r'^pracovní poměr$': ('employment_types', parse_set),
        r'^nadpis pracovní nabídky$': ('title', parse_text),
        r'^odkaz na webové stránky firmy$': ('company_link', parse_text),
        r'^email address$': ('email', parse_text),
        r'^je práce na dálku\?$': ('remote', parse_boolean_words),
        r'^město, kde se nachází kancelář$': ('locations_raw', parse_locations),
        r'^text pracovní nabídky$': ('description_html', parse_markdown),
        r'^externí odkaz na pracovní nabídku$': ('link', parse_text),
        r'^varianta z ceníku$': ('pricing_plan', parse_pricing_plan),
        r'^approved$': ('approved_at', parse_date),
        r'^expire[ds]$': ('expires_at', parse_date),
    }, record)
    data['id'] = create_id(data['posted_at'], data['company_link'])
    return data


def parse_locations(location):
    if location:
        return [loc.strip() for loc in re.split(r'\snebo\s', location)]
    return []


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
