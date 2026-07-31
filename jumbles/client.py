import json, os, urllib.request, urllib.error
from datetime import datetime as dt


class JumbleClient:
    """Fetch, parse, and cache daily Jumble puzzles from Tribune Content Agency."""

    api_url = 'https://puzzles.tribunecontentagency.com/puzzles/pzzResource/puzzle.do'
    api_data = (
        'apiKey=e06317ec9b0e52363f404c73f8b681b926908f6c22dd46f86040e5fea0e96879'
        '&productId=jumbledaily&publicationDate=&prvNxt=&langCode=en-US&ldt='
    )
    date_fmt = '%m/%d/%Y'
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36',
        'Origin': 'https://puzzles.tribunecontentagency.com',
        'Referer': 'https://puzzles.tribunecontentagency.com/puzzles/jumble/jumble.do',
        'X-Requested-With': 'XMLHttpRequest',
    }
    cache_dir = os.path.expanduser('~/.cache/jumble')

    def __init__(self):
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_jumble(self, date=None):
        """Return parsed puzzle dict. If date is None, fetch today's."""
        date = date or dt.today()
        date_str = dt.strftime(date, self.date_fmt)
        cache_file = f'{self.cache_dir}/{date_str.replace("/", "")}.json'
        data = self._fetch_from_api(date_str)
        parsed = self._parse(data)
        # ponytail: naive date-based cache filename, eviction if it matters
        with open(cache_file, 'w') as f:
            json.dump(parsed, f)
        return parsed

    def _fetch_from_api(self, date_str):
        data = self.api_data + date_str
        req = urllib.request.Request(self.api_url, data=data.encode(), headers=self.headers, method='POST')
        try:
            resp = urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'TCA API error ({e.code}): {e.read().decode()[:200]}')
        return json.loads(resp.read().decode())

    @staticmethod
    def _parse(resp):
        det = resp['puzzleDetails']
        bon = det['bonusPuzzle']
        img = (resp.get('cdata') or [{}])[0].get('resourceLocation', '')
        return {
            'date': det['date'],
            'clues': [JumbleClient._parse_clue(c) for c in det['clues']],
            'caption': bon['caption'],
            'layout': JumbleClient._parse_layout(bon['solutions']),
            'answer': ''.join(w['word'] for w in bon['solutions']),
            'image': img,
        }

    @staticmethod
    def _parse_clue(c):
        return {
            'jumbled': c['word'],
            'answer': c['answer'],
            'circles': [int(v) for v in c['shape']['value'].split(',')],
        }

    @staticmethod
    def _parse_layout(solutions):
        parts = []
        for s in solutions:
            pre = s.get('prefix') or ''
            suf = s.get('suffix') or ''
            parts.append(pre + ('_' * len(s['word'])) + suf)
        return ' '.join(parts)