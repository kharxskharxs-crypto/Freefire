#!/usr/bin/env python3
"""อัปเดตราคาสินค้าอัตโนมัติ: อ่านหน้าสินค้าจากรายการใน price-sources.json แล้วเขียนผลลง prices.json
- เรียกเว็บร้านแค่วันละครั้ง ทีละหน้า เว้นระยะ 3 วินาที (เบามาก)
- ถ้าอ่านราคาไม่ได้ หรือราคาที่อ่านได้ดูผิดปกติ (ห่างจากราคาเดิมเกิน 40%) จะไม่เปลี่ยนราคาเดิม
- รัน `python update_prices.py --selftest` เพื่อทดสอบตัวอ่านราคาโดยไม่ต้องต่อเน็ต
"""
import json, re, sys, time, os
import urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta

SOURCES, OUT = 'price-sources.json', 'prices.json'
UA = 'Mozilla/5.0 (compatible; PCBuilderTH-price-check/1.0; school project; once a day)'
BAND = 0.40          # ยอมรับราคาที่ต่างจากราคาอ้างอิงไม่เกิน 40%
DELAY = 3            # วินาทีระหว่างแต่ละหน้า


def to_num(s):
    try:
        return float(str(s).replace(',', '').strip())
    except ValueError:
        return None


def candidates(html):
    """ดึงตัวเลขที่น่าจะเป็นราคาจากหน้าเว็บหลายแบบ (JSON-LD, meta, ข้อความใกล้คำว่า 'ราคา', สัญลักษณ์ ฿)"""
    found = []
    for m in re.finditer(r'"(?:price|lowPrice|salePrice)"\s*:\s*"?([0-9][0-9,]*(?:\.[0-9]+)?)"?', html):
        found.append(('json', to_num(m.group(1))))
    for m in re.finditer(r'<meta[^>]+(?:product:price:amount|og:price:amount|itemprop=["\']price["\'])[^>]*content=["\']([0-9,\.]+)["\']', html, re.I):
        found.append(('meta', to_num(m.group(1))))
    for m in re.finditer(r'itemprop=["\']price["\'][^>]*content=["\']([0-9,\.]+)["\']', html, re.I):
        found.append(('meta', to_num(m.group(1))))
    for m in re.finditer(r'ราคา[^0-9<]{0,40}([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{3,6})', html):
        found.append(('text', to_num(m.group(1))))
    for m in re.finditer(r'[฿]\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{3,6})', html):
        found.append(('baht', to_num(m.group(1))))
    return [(k, v) for k, v in found if v]


def pick_price(html, ref):
    """เลือกราคาที่อยู่ในช่วงใกล้ราคาอ้างอิง และพบซ้ำบ่อยที่สุด"""
    lo, hi = ref * (1 - BAND), ref * (1 + BAND)
    ok = [v for _, v in candidates(html) if lo <= v <= hi]
    if not ok:
        return None
    return Counter(round(v) for v in ok).most_common(1)[0][0]


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'th,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read()
        enc = r.headers.get_content_charset() or 'utf-8'
    return raw.decode(enc, 'replace')


def load(path, default):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return default


def main():
    sources = load(SOURCES, [])
    prev = load(OUT, {'updated': None, 'items': []})
    prev_by = {i['name']: i for i in prev.get('items', [])}
    today = (datetime.now(timezone.utc) + timedelta(hours=7)).strftime('%Y-%m-%d')
    items, ok_n, fail_n = [], 0, 0
    for n, s in enumerate(sources):
        name, url = s['name'], s['url']
        old = prev_by.get(name)
        ref = (old or {}).get('price') or s.get('base')
        if not ref:
            print('ข้าม (ไม่มีราคาอ้างอิง):', name)
            continue
        try:
            price = pick_price(fetch(url), ref)
        except Exception as e:  # noqa: BLE001
            price, err = None, repr(e)
        else:
            err = 'อ่านราคาไม่ได้หรือราคาผิดปกติ'
        if price:
            ok_n += 1
            print('OK  ', name, ref, '->', price)
            items.append({'name': name, 'shop': s.get('shop', 'ร้านค้า'), 'url': url, 'price': price, 'd': today})
        else:
            fail_n += 1
            print('FAIL', name, '-', err)
            if old:  # คงราคาเดิมและวันที่เดิมไว้
                items.append(old)
        if n < len(sources) - 1:
            time.sleep(DELAY)
    if sources and ok_n == 0:
        print('ไม่สำเร็จเลยสักรายการ ไม่แก้ prices.json')
        sys.exit(1)
    result = {'updated': today if ok_n else prev.get('updated'), 'items': items}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print('เสร็จ: สำเร็จ', ok_n, 'ล้มเหลว', fail_n)


def selftest():
    cases = [
        ('jsonld', '<script type="application/ld+json">{"offers":{"price":"4,590","priceCurrency":"THB"}}</script>', 4500, 4590),
        ('meta', '<meta property="product:price:amount" content="4590.00">', 4500, 4590),
        ('text', '<div>ราคาล่าสุด 4,590 บาท</div><div>ผ่อน 0% 459 บาท</div>', 4500, 4590),
        ('baht', '<span>฿4,590</span><span>฿99,000</span>', 4500, 4590),
        ('out-of-band', '<span>฿99,000</span>', 4500, None),
        ('empty', '<html></html>', 4500, None),
    ]
    bad = 0
    for name, html, ref, want in cases:
        got = pick_price(html, ref)
        print(('ผ่าน' if got == want else 'ไม่ผ่าน'), name, got)
        bad += got != want
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    selftest() if '--selftest' in sys.argv else main()
