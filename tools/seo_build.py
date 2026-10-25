# -*- coding: utf-8 -*-
"""
SaeVocalLab SEO / AI検索 対策ファイルの自動生成スクリプト

実行方法（サイトのフォルダで）:
    python3 tools/seo_build.py

これ1回で、次のものをまとめて作り直します。
  1. 各ページ <head> の「SEO自動生成ブロック」
     - 正式URL（canonical）、og:url / og:image / og:site_name / og:locale、Twitterカード、apple-touch-icon
     - 構造化データ（JSON-LD）：教室情報 / サイト情報 / ページ情報 / パンくず / レッスン（コース） / よくあるご質問
  2. sitemap.xml
  3. robots.txt
  4. llms.txt（AI向けのサイト概要）
  5. 公開前チェック（タイトル・説明文の長さ、重複、h1の数、alt の付け忘れ、仮の電話番号）

【ルール】仮原稿は構造化データに入れない
  - 下の SCHOOL で None のままの項目は出力しません。
  - 「よくあるご質問」は FAQ_CONFIRMED に入れたページだけ出力します（原稿を確認してから追加）。
  - 「生徒さんの声」は、Googleのガイドライン上、自社サイトの口コミとして構造化データに入れないため出力しません。

必要なもの: Python 3 と beautifulsoup4（pip install beautifulsoup4）
"""
import json
import pathlib
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# ============================================================
# 設定（公開前にここを確認・入力）
# ============================================================

# 公開するドメイン（末尾スラッシュなし）
SITE_URL = 'https://saevocallab.jp'

SCHOOL = {
    'name': 'SaeVocalLab',
    'alternateName': ['サエ ボーカル ラボ', 'サエボーカルラボ'],
    'description': '西武池袋線「中村橋駅」より徒歩1分のボーカル専門教室。お子様からシニアまで、マンツーマンの個人レッスン。30分の無料体験レッスン受付中。',
    'postalCode': '176-0023',
    'addressRegion': '東京都',
    'addressLocality': '練馬区',
    'streetAddress': '中村北4-4-13',
    'nearestStation': '西武池袋線「中村橋駅」より徒歩1分',
    'geo': (35.735584, 139.638275),
    'logo': 'assets/img/logo.png',
    'image': 'assets/img/ogp.jpg',
    'areaServed': ['練馬区'],
    # 月謝（サイト掲載の内容）
    'price': {'name': 'ボーカルレッスン 月謝（月2回・1回50分）', 'price': 12000},
    # 営業時間（日曜・祝日はお休み）。label は llms.txt 用の表記。
    'openingHours': [
        {'days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], 'opens': '10:00', 'closes': '21:00',
         'label': '月〜金 10:00〜21:00（最終受付20:00）'},
        {'days': ['Saturday'], 'opens': '12:00', 'closes': '18:00',
         'label': '土 12:00〜18:00（最終受付17:00）'},
    ],
    'closedLabel': '日曜・祝日',

    # ---- ここから下は確定したら入力（None / 空のままなら出力されません） ----
    # 電話番号は掲載しない方針のため、構造化データ・llms.txt に出力しません。
    # お申し込み用メールアドレス・LINE公式アカウント（友だち追加URL）
    'email': 'ririkaman1113@gmail.com',
    'line': 'https://lin.ee/gzu6Sca',
    # 講師名（構造化データでは「講師」として出力）
    'instructor': 'sae',
    # 外部アカウントのURL（SNSはInstagramのみ）。Googleビジネスプロフィールを作ったらそのURLも追加。
    # 例: ['https://www.instagram.com/xxxx/', 'https://maps.app.goo.gl/xxxx']
    'sameAs': [],
}

# 各レッスンページ。名前・説明はページ内の見出しとリード文から自動で読み取ります。
# serviceType は検索で使われやすい言葉を指定します。
LESSONS = {
    'lesson/vocal.html': {'serviceType': 'ボーカルレッスン', 'audience': None},
    'lesson/voice-training.html': {'serviceType': 'ボイストレーニング', 'audience': None},
    'lesson/kids.html': {'serviceType': 'キッズボーカルレッスン', 'audience': '子ども'},
    'lesson/adult.html': {'serviceType': '大人・シニア向けボーカルレッスン', 'audience': '大人・シニア'},
    'lesson/sing-play.html': {'serviceType': '弾き語りレッスン', 'audience': None},
    'lesson/audition.html': {'serviceType': 'オーディション・受験対策レッスン', 'audience': None},
}

# 「よくあるご質問」を構造化データに出すページ。回答を確認したページをここに追加して再実行。
# 例: FAQ_CONFIRMED = {'index.html', 'lesson/kids.html'}
# トップのFAQはサイト掲載の事実（料金・時間・所在地・申込方法）だけで書いているため出力対象にしています。
FAQ_CONFIRMED = {'index.html'}

# サイトマップから除外するページ
SITEMAP_EXCLUDE = set()

PRIORITY = {'index.html': '1.0'}  # それ以外のレッスンページは 0.8

# AIの巡回を許可するか（True=許可）。止めたいものは False に。
AI_CRAWLERS = {
    'GPTBot': True,            # OpenAI（学習用）
    'OAI-SearchBot': True,     # ChatGPT 検索
    'ChatGPT-User': True,      # ChatGPT がユーザーの依頼で閲覧
    'ClaudeBot': True,         # Anthropic（学習用）
    'Claude-SearchBot': True,  # Claude 検索
    'Claude-User': True,       # Claude がユーザーの依頼で閲覧
    'PerplexityBot': True,     # Perplexity
    'Google-Extended': True,   # Gemini 等での利用
    'Applebot-Extended': True, # Apple Intelligence
}

# 公開前チェックの目安（文字数）
TITLE_MAX = 40
DESC_MIN, DESC_MAX = 70, 130
PLACEHOLDER_TEL = '000-0000-0000'

# ============================================================

ROOT = pathlib.Path(__file__).resolve().parent.parent
START = '<!-- SEO:START（tools/seo_build.py が自動生成。直接編集しないでください） -->'
END = '<!-- SEO:END -->'
BLOCK_RE = re.compile(r'[ \t]*<!-- SEO:START.*?<!-- SEO:END -->\n?', re.S)


def rel(p):
    return p.relative_to(ROOT).as_posix()


def abs_url(path=''):
    path = path.lstrip('/')
    if path == 'index.html':
        path = ''
    return f'{SITE_URL}/{path}'


def resolve(page, href):
    """ページ内の相対リンクを絶対URLにする（index.html は / に揃える）"""
    u = urljoin(abs_url(page) if page != 'index.html' else SITE_URL + '/index.html', href)
    return re.sub(r'/index\.html(?=$|#)', '/', u)


ORG_ID = abs_url() + '#school'
SITE_ID = abs_url() + '#website'


def clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def text_of(soup, sel):
    el = soup.select_one(sel)
    return clean(el.get_text()) if el else ''


def place():
    s = SCHOOL
    return {'@type': 'PostalAddress', 'postalCode': s['postalCode'], 'addressCountry': 'JP',
            'addressRegion': s['addressRegion'], 'addressLocality': s['addressLocality'],
            'streetAddress': s['streetAddress']}


def school():
    s = SCHOOL
    lat, lng = s['geo']
    org = {
        '@type': ['MusicSchool', 'LocalBusiness'],
        '@id': ORG_ID,
        'name': s['name'],
        'alternateName': s['alternateName'],
        'description': s['description'],
        'url': abs_url(),
        'logo': abs_url(s['logo']),
        'image': abs_url(s['image']),
        'address': place(),
        'geo': {'@type': 'GeoCoordinates', 'latitude': lat, 'longitude': lng},
        'hasMap': f'https://www.google.com/maps/search/?api=1&query={lat}%2C{lng}',
        'knowsAbout': ['ボーカルレッスン', 'ボイストレーニング', '発声', 'キッズボーカル', '弾き語り',
                       'オーディション対策', '音楽科受験対策'],
        'hasOfferCatalog': {
            '@type': 'OfferCatalog', 'name': 'レッスン一覧',
            'itemListElement': [{'@type': 'Offer', 'itemOffered': {'@id': abs_url(p) + '#course'}} for p in LESSONS],
        },
    }
    if s.get('areaServed'):
        org['areaServed'] = [{'@type': 'AdministrativeArea', 'name': a} for a in s['areaServed']]
    if s.get('openingHours'):
        org['openingHoursSpecification'] = [
            {'@type': 'OpeningHoursSpecification', 'dayOfWeek': h['days'], 'opens': h['opens'], 'closes': h['closes']}
            for h in s['openingHours']]
    if s.get('price'):
        org['makesOffer'] = {
            '@type': 'Offer', 'name': s['price']['name'],
            'priceSpecification': {'@type': 'UnitPriceSpecification', 'price': s['price']['price'],
                                   'priceCurrency': 'JPY', 'unitText': '月', 'valueAddedTaxIncluded': True}}
        org['priceRange'] = f'月謝 {s["price"]["price"]:,}円（税込）'
    if s.get('email'):
        org['email'] = s['email']
    if s.get('email') or s.get('line'):
        cp = {'@type': 'ContactPoint', 'contactType': '無料体験レッスンのお申し込み・お問い合わせ',
              'availableLanguage': 'ja'}
        if s.get('email'):
            cp['email'] = s['email']
        if s.get('line'):
            cp['url'] = s['line']
        org['contactPoint'] = cp
    if s.get('instructor'):
        org['employee'] = {'@type': 'Person', 'name': s['instructor'], 'jobTitle': 'ボーカル講師'}
    if s.get('sameAs'):
        org['sameAs'] = s['sameAs']
    return org


def website():
    return {'@type': 'WebSite', '@id': SITE_ID, 'url': abs_url(), 'name': SCHOOL['name'],
            'alternateName': SCHOOL['alternateName'], 'inLanguage': 'ja', 'publisher': {'@id': ORG_ID}}


def page_image(soup, page):
    if page in LESSONS:
        img = soup.select_one('.page-hero img')
        if img and img.get('src'):
            return resolve(page, img['src'])
    return abs_url(SCHOOL['image'])


def webpage(soup, page):
    wp = {'@type': 'WebPage', '@id': abs_url(page) + '#webpage', 'url': abs_url(page),
          'name': clean(soup.title.get_text()) if soup.title else '',
          'isPartOf': {'@id': SITE_ID}, 'about': {'@id': ORG_ID}, 'inLanguage': 'ja',
          'primaryImageOfPage': {'@type': 'ImageObject', 'url': page_image(soup, page)}}
    desc = soup.find('meta', attrs={'name': 'description'})
    if desc:
        wp['description'] = desc['content']
    if page in LESSONS:
        wp['mainEntity'] = {'@id': abs_url(page) + '#course'}
    return wp


def breadcrumb(soup, page):
    ol = soup.select_one('.breadcrumb')
    if not ol:
        return None
    items = []
    for i, li in enumerate(ol.select('li'), 1):
        a = li.find('a')
        items.append({'@type': 'ListItem', 'position': i, 'name': clean(li.get_text()),
                      'item': resolve(page, a['href']) if a else abs_url(page)})
    return {'@type': 'BreadcrumbList', 'itemListElement': items}


def course(soup, page):
    if page not in LESSONS:
        return None
    info = LESSONS[page]
    name = text_of(soup, '.page-hero__title')
    lead = text_of(soup, '.page-hero__lead')
    intro = text_of(soup, '.page-hero__intro')
    c = {'@type': 'Course', '@id': abs_url(page) + '#course', 'name': name,
         'description': f'{lead}{intro}', 'url': abs_url(page), 'image': page_image(soup, page),
         'inLanguage': 'ja', 'provider': {'@id': ORG_ID}, 'educationalLevel': '初心者から経験者まで',
         'about': info['serviceType'],
         'hasCourseInstance': {'@type': 'CourseInstance', 'courseMode': 'onsite',
                               'courseWorkload': 'PT50M',
                               'location': {'@type': 'Place', 'name': SCHOOL['name'], 'address': place()}}}
    if SCHOOL.get('instructor'):
        c['hasCourseInstance']['instructor'] = {'@type': 'Person', 'name': SCHOOL['instructor']}
    if info.get('audience'):
        c['audience'] = {'@type': 'Audience', 'audienceType': info['audience']}
    if SCHOOL.get('price'):
        c['offers'] = {'@type': 'Offer', 'category': '月謝', 'price': SCHOOL['price']['price'],
                       'priceCurrency': 'JPY', 'url': abs_url(page)}
    return c


def faq(soup, page):
    if page not in FAQ_CONFIRMED:
        return None
    qa = []
    for item in soup.select('.faq__item'):
        q, a = item.select_one('.faq__q'), item.select_one('.faq__a')
        if not (q and a):
            continue
        q, a = BeautifulSoup(str(q), 'html.parser'), BeautifulSoup(str(a), 'html.parser')
        for mark in q.select('.faq__mark, .faq__toggle') + a.select('.faq__mark'):
            mark.decompose()
        qa.append({'@type': 'Question', 'name': clean(q.get_text()),
                   'acceptedAnswer': {'@type': 'Answer', 'text': clean(a.get_text())}})
    return {'@type': 'FAQPage', '@id': abs_url(page) + '#faq', 'mainEntity': qa} if qa else None


def build_block(html, page):
    soup = BeautifulSoup(html, 'html.parser')
    graph = [school(), website(), webpage(soup, page)]
    for node in (breadcrumb(soup, page), course(soup, page), faq(soup, page)):
        if node:
            graph.append(node)
    ld = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, indent=2)
    root = '../' * page.count('/')
    title = clean(soup.title.get_text()) if soup.title else SCHOOL['name']
    lines = [
        START,
        f'<link rel="canonical" href="{abs_url(page)}">',
        f'<meta property="og:url" content="{abs_url(page)}">',
        f'<meta property="og:image" content="{page_image(soup, page)}">',
        f'<meta property="og:site_name" content="{SCHOOL["name"]}">',
        '<meta property="og:locale" content="ja_JP">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<link rel="apple-touch-icon" href="{root}assets/img/apple-touch-icon.png">',
        '<script type="application/ld+json">',
        ld,
        '</script>',
        END,
    ]
    return '\n'.join(lines), [n['@type'] for n in graph[3:]], title


def pages_list():
    return [ROOT / 'index.html'] + sorted((ROOT / 'lesson').glob('*.html'))


def update_pages():
    pages = pages_list()
    for p in pages:
        page = rel(p)
        html = BLOCK_RE.sub('', p.read_text(encoding='utf-8'))
        block, extra, _ = build_block(html, page)
        html = html.replace('</head>', block + '\n</head>', 1)
        p.write_text(html, encoding='utf-8')
        print(f'  {page:28s} 更新  ' + ' / '.join(t if isinstance(t, str) else t[0] for t in extra))
    return pages


def write_sitemap(pages):
    today = date.today().isoformat()
    rows = []
    for p in pages:
        page = rel(p)
        if page in SITEMAP_EXCLUDE:
            continue
        rows.append(f'  <url>\n    <loc>{abs_url(page)}</loc>\n    <lastmod>{today}</lastmod>\n'
                    f'    <priority>{PRIORITY.get(page, "0.8")}</priority>\n  </url>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(rows) + '\n</urlset>\n')
    (ROOT / 'sitemap.xml').write_text(xml, encoding='utf-8')


def write_robots():
    lines = ['# robots.txt（tools/seo_build.py が自動生成）', '', 'User-agent: *', 'Allow: /', '']
    lines.append('# AI検索・AIアシスタントの巡回設定')
    for bot, ok in AI_CRAWLERS.items():
        lines += [f'User-agent: {bot}', 'Allow: /' if ok else 'Disallow: /', '']
    lines.append(f'Sitemap: {abs_url("sitemap.xml")}')
    (ROOT / 'robots.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def write_llms(pages):
    s = SCHOOL
    out = [f'# {s["name"]}（{s["alternateName"][0]}）', '', f'> {s["description"]}', '',
           '## 教室情報',
           f'- 教室名: {s["name"]}（{s["alternateName"][0]}）',
           f'- 所在地: 〒{s["postalCode"]} {s["addressRegion"]}{s["addressLocality"]}{s["streetAddress"]}',
           f'- 最寄り駅: {s["nearestStation"]}']
    if s.get('openingHours'):
        hours = '、'.join(h['label'] for h in s['openingHours'])
        if s.get('closedLabel'):
            hours += f'。{s["closedLabel"]}はお休み'
        out.append(f'- 営業時間: {hours}')
    if s.get('email'):
        out.append(f'- メール: {s["email"]}')
    out += ['- レッスン形式: マンツーマンの個人レッスン（1回50分、曜日・時間固定）']
    if s.get('price'):
        out.append(f'- 料金: {s["price"]["name"]} {s["price"]["price"]:,}円（税込）')
    out += ['- 無料体験: 30分の無料体験レッスンあり（手ぶらで参加可）',
            '- 申し込み方法: メールまたはLINE（電話での受付は行っていません）']
    if s.get('line'):
        out.append(f'- LINE: {s["line"]}')
    if s.get('instructor'):
        out.append(f'- 講師: {s["instructor"]}')
    out += ['', '## レッスン']
    for page in LESSONS:  # サイトの掲載順
        soup = BeautifulSoup((ROOT / page).read_text(encoding='utf-8'), 'html.parser')
        out.append(f'- [{text_of(soup, ".page-hero__title")}]({abs_url(page)}): {text_of(soup, ".page-hero__lead")}')
    out += ['', '## 主なページ', f'- [トップページ]({abs_url()})']
    for anchor, label in [('lesson', 'レッスン一覧'), ('course', 'コース・料金'), ('instructor', '講師紹介'),
                          ('faq', 'よくあるご質問'), ('access', 'アクセス'), ('contact', 'お申込み・お問合せ')]:
        out.append(f'- [{label}]({abs_url()}#{anchor})')
    (ROOT / 'llms.txt').write_text('\n'.join(out) + '\n', encoding='utf-8')


def check(pages):
    """公開前チェック。問題があれば一覧で表示（ファイルは変更しない）"""
    warn, titles, descs = [], {}, {}
    for p in pages:
        page = rel(p)
        html = p.read_text(encoding='utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        t = clean(soup.title.get_text()) if soup.title else ''
        m = soup.find('meta', attrs={'name': 'description'})
        d = m['content'] if m else ''
        if not t:
            warn.append(f'{page}: title がありません')
        elif len(t) > TITLE_MAX:
            warn.append(f'{page}: title が{len(t)}文字（目安{TITLE_MAX}文字以内。検索結果で後ろが切れる場合あり）')
        if not d:
            warn.append(f'{page}: description がありません')
        elif not DESC_MIN <= len(d) <= DESC_MAX:
            warn.append(f'{page}: description が{len(d)}文字（目安{DESC_MIN}〜{DESC_MAX}文字）')
        titles.setdefault(t, []).append(page)
        descs.setdefault(d, []).append(page)
        h1 = len(soup.find_all('h1'))
        if h1 != 1:
            warn.append(f'{page}: h1 が{h1}個（1個が目安）')
        for img in soup.find_all('img'):
            if not img.has_attr('alt'):
                warn.append(f'{page}: alt のない画像 {img.get("src")}')
        if PLACEHOLDER_TEL in html or 'href="tel:' in html:
            warn.append(f'{page}: 電話番号が残っています（電話番号は掲載しない方針）')
        empty = html.count('href="#"')
        if empty:
            warn.append(f'{page}: リンク先が未設定のボタン（href="#"）が{empty}か所あります')
        for a in soup.find_all('a', href=True):
            h = a['href'].split('#')[0].split('?')[0]
            if h and not re.match(r'^(https?:|mailto:|tel:)', h) and not (p.parent / h).resolve().exists():
                warn.append(f'{page}: リンク切れ {a["href"]}')
    for t, ps in titles.items():
        if t and len(ps) > 1:
            warn.append(f'title が重複: {", ".join(ps)}')
    for d, ps in descs.items():
        if d and len(ps) > 1:
            warn.append(f'description が重複: {", ".join(ps)}')
    print('\n公開前チェック:')
    print('\n'.join('  ・' + w for w in warn) if warn else '  問題は見つかりませんでした。')


if __name__ == '__main__':
    print(f'ドメイン: {SITE_URL}')
    print('ページを更新:')
    pages = update_pages()
    write_sitemap(pages)
    write_robots()
    write_llms(pages)
    print('sitemap.xml / robots.txt / llms.txt を作成しました。')
    print('※ よくあるご質問の構造化データ出力: ' + (', '.join(sorted(FAQ_CONFIRMED)) or 'なし') + '（FAQ_CONFIRMED）')
    if not SCHOOL.get('sameAs'):
        print('※ Instagram のURLが未入力です（SCHOOL[\'sameAs\']）。サイト内のInstagramボタンのリンク先も未設定です。')
    check(pages)
