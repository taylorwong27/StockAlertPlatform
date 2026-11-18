"""Return recent, display-ready news for the Stock Alert Platform."""

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

import requests
import yfinance as yf


LOGGER = logging.getLogger(__name__)
MAX_NEWS = 5
ATOM = '{http://www.w3.org/2005/Atom}'
COMPANIES = {'AAPL': 'Apple', 'MSFT': 'Microsoft', 'NVDA': 'NVIDIA'}
OFFICIAL_FEEDS = {
    'AAPL': ('Apple Newsroom', 'https://www.apple.com/newsroom/rss-feed.rss'),
    'MSFT': ('Microsoft Azure Blog', 'https://azure.microsoft.com/en-us/blog/feed/'),
    'NVDA': ('NVIDIA Newsroom', 'https://nvidianews.nvidia.com/cats/press_release.xml'),
}


def _text(value):
    return ' '.join(value.split()) if isinstance(value, str) else ''


def _url(value):
    if not isinstance(value, str) or re.search(r'[\s\x00-\x1f\x7f\\]', value):
        return ''
    try:
        parsed = urlsplit(value)
        if parsed.scheme in {'https', 'http'} and parsed.hostname and not parsed.username and not parsed.password:
            return value
    except ValueError:
        pass
    return ''


def _published_utc(value):
    if not isinstance(value, str) or not value.strip():
        return ''
    try:
        try:
            date = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        except ValueError:
            date = parsedate_to_datetime(value)
        if date.utcoffset() is not None:
            return date.astimezone(timezone.utc).isoformat(timespec='seconds')
    except (ValueError, OverflowError):
        pass
    return ''


def _matches_company(content, ticker):
    finance = content.get('finance')
    tags = finance.get('stockTickers') if isinstance(finance, dict) else None
    if isinstance(tags, list) and any(isinstance(tag, str) and tag.upper() == ticker for tag in tags):
        return True
    terms = [ticker]
    if ticker in COMPANIES:
        terms.append(COMPANIES[ticker])
    pattern = r'(?<!\w)(?:' + '|'.join(re.escape(term) for term in terms) + r')(?!\w)'
    headline = _text(content.get('title'))
    summary = _text(content.get('summary'))
    return re.search(pattern, f'{headline} {summary}', re.IGNORECASE) is not None


def _yahoo_news(ticker):
    for entry in yf.Ticker(ticker).get_news(count=10) or []:
        content = entry.get('content') if isinstance(entry, dict) else None
        if not isinstance(content, dict) or not _matches_company(content, ticker):
            continue
        provider = content.get('provider')
        links = [content.get('canonicalUrl'), content.get('clickThroughUrl')]
        yield {
            'title': content.get('title'),
            'source': provider.get('displayName') if isinstance(provider, dict) else '',
            'published_at': content.get('pubDate'),
            'url': next((link['url'] for link in links if isinstance(link, dict) and _url(link.get('url'))), ''),
        }


def _feed_news(ticker):
    source, feed_url = OFFICIAL_FEEDS[ticker]
    response = requests.get(feed_url, timeout=(3.05, 6))
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    feed_host = urlsplit(feed_url).hostname

    # Each feed belongs to the company named in OFFICIAL_FEEDS. Its entries
    # need not repeat the company name in every headline to be relevant.
    if root.tag == f'{ATOM}feed':
        for entry in root.findall(f'{ATOM}entry'):
            links = entry.findall(f'{ATOM}link')
            yield {
                'title': entry.findtext(f'{ATOM}title'),
                'source': source,
                'published_at': entry.findtext(f'{ATOM}published') or entry.findtext(f'{ATOM}updated'),
                'url': next((link.get('href') for link in links if link.get('rel', 'alternate') == 'alternate'), ''),
            }
        return

    for entry in root.findall('./channel/item'):
        link = _url(entry.findtext('link'))
        # Some feeds syndicate other sites. Keep only links published on this feed's own site.
        if not link or urlsplit(link).hostname != feed_host:
            continue
        yield {
            'title': entry.findtext('title'),
            'source': source,
            'published_at': entry.findtext('pubDate'),
            'url': link,
        }


def _clean_news(records, limit):
    clean = []
    for item in records:
        article = {
            'title': _text(item.get('title')),
            'source': _text(item.get('source')),
            'published_at': _published_utc(item.get('published_at')),
            'url': _url(item.get('url')),
        }
        if all(article.values()):
            clean.append(article)

    clean.sort(key=lambda item: item['published_at'], reverse=True)
    titles, urls, result = set(), set(), []
    for article in clean:
        title_key = article['title'].casefold()
        parsed = urlsplit(article['url'])
        query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
                 if not key.lower().startswith('utm_')]
        url_key = urlunsplit(('', parsed.netloc.lower(), parsed.path.rstrip('/'), urlencode(sorted(query)), ''))
        if title_key in titles or url_key in urls:
            continue
        titles.add(title_key)
        urls.add(url_key)
        result.append(article)
        if len(result) == limit:
            break
    return result


def get_stock_news(ticker: str, limit: int = 5) -> list[dict[str, str]]:
    """Return up to five articles, newest first, or [] if news is unavailable."""
    if not isinstance(ticker, str) or type(limit) is not int or limit < 1:
        return []
    ticker = ticker.strip().upper()
    if re.fullmatch(r'[A-Z0-9][A-Z0-9.\-]{0,14}', ticker) is None:
        return []
    limit = min(limit, MAX_NEWS)

    try:
        articles = _clean_news(_yahoo_news(ticker), limit)
    except Exception as error:
        # A third-party news outage must not prevent the price and signal panels from rendering.
        LOGGER.warning('Yahoo news unavailable for %s (%s)', ticker, type(error).__name__)
        articles = []
    if articles or ticker not in OFFICIAL_FEEDS:
        return articles

    try:
        return _clean_news(_feed_news(ticker), limit)
    except (requests.RequestException, ElementTree.ParseError) as error:
        LOGGER.warning('Official news feed unavailable for %s (%s)', ticker, type(error).__name__)
        return []


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tickers', nargs='+', help='Stock symbols, for example AAPL MSFT NVDA')
    parser.add_argument('--limit', type=int, default=MAX_NEWS)
    arguments = parser.parse_args()
    news = {ticker.strip().upper(): get_stock_news(ticker, arguments.limit) for ticker in arguments.tickers}
    print(json.dumps(news, ensure_ascii=True, indent=2))
