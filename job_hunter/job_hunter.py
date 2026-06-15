#!/usr/bin/env python3
"""
🤖 Saudi Tech Job Hunter
يبحث يومياً عن وظايف تقنية/AI/IT في المملكة العربية السعودية
ويولد مسودة إيميل جاهزة للإرسال
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
import json
import os
import xml.etree.ElementTree as ET
import urllib.parse

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
}

KEYWORDS = [
    "Artificial Intelligence",
    "Machine Learning",
    "Data Science",
    "Software Engineer",
    "DevOps",
    "Cloud Engineer",
    "Cybersecurity",
    "Data Engineer",
    "IT Specialist",
    "RPA Automation",
    "Python Developer",
    "AI Engineer",
]

LOCATION = "Saudi Arabia"


# ─────────────────────────────────────────────
#  المصادر
# ─────────────────────────────────────────────

def fetch_indeed(keyword: str) -> list:
    """Indeed RSS feed (Saudi Arabia)"""
    jobs = []
    q = urllib.parse.quote(keyword)
    url = f"https://sa.indeed.com/rss?q={q}&l=Saudi+Arabia&sort=date&fromage=1"
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        root = ET.fromstring(r.content)
        channel = root.find("channel")
        if channel is None:
            return jobs
        for item in channel.findall("item")[:4]:
            title = item.findtext("title", "").strip()
            link  = item.findtext("link",  "").strip()
            desc  = item.findtext("description", "").strip()
            # استخلص اسم الشركة من الوصف
            company = "غير محدد"
            soup = BeautifulSoup(desc, "lxml")
            text = soup.get_text(" ", strip=True)
            if " - " in text:
                parts = text.split(" - ")
                if len(parts) >= 2:
                    company = parts[1].strip()
            jobs.append({
                "title":   title,
                "company": company,
                "link":    link,
                "source":  "Indeed 🇸🇦",
            })
    except Exception:
        pass
    return jobs


def fetch_bayt(keyword: str) -> list:
    """Bayt.com – أكبر موقع وظايف في الشرق الأوسط"""
    jobs = []
    slug = keyword.lower().replace(" ", "-")
    url  = f"https://www.bayt.com/en/saudi-arabia/jobs/{slug}-jobs/"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.content, "lxml")
        cards = soup.select("li[data-js-job]")[:4]
        for card in cards:
            title_el   = card.select_one("h2 a")
            company_el = card.select_one("b[itemprop='name']")
            link_el    = card.select_one("h2 a")
            if not title_el:
                continue
            href = link_el.get("href", "") if link_el else ""
            jobs.append({
                "title":   title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True) if company_el else "غير محدد",
                "link":    f"https://www.bayt.com{href}" if href else "",
                "source":  "Bayt.com",
            })
    except Exception:
        pass
    return jobs


def fetch_linkedin(keyword: str) -> list:
    """LinkedIn public job listings (بدون تسجيل دخول)"""
    jobs = []
    q   = urllib.parse.quote(keyword)
    url = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={q}&location=Saudi%20Arabia&f_TPR=r86400&start=0"
    )
    try:
        r    = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.content, "lxml")
        cards = soup.select("li")[:4]
        for card in cards:
            title_el   = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            link_el    = card.select_one("a.base-card__full-link")
            if not title_el:
                continue
            jobs.append({
                "title":   title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True) if company_el else "غير محدد",
                "link":    link_el.get("href", "").split("?")[0] if link_el else "",
                "source":  "LinkedIn",
            })
    except Exception:
        pass
    return jobs


def fetch_jadarat() -> list:
    """منصة جدارات – بوابة التوظيف الحكومية السعودية"""
    jobs = []
    url  = "https://jadarat.sa/api/v1/jobs?q=technology&category=IT&limit=10"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=12)
        data = r.json()
        items = data.get("data", data.get("jobs", []))[:5]
        for item in items:
            jobs.append({
                "title":   item.get("title", item.get("jobTitle", "")).strip(),
                "company": item.get("company", item.get("organization", "غير محدد")).strip(),
                "link":    item.get("url", item.get("applyLink", "https://jadarat.sa")).strip(),
                "source":  "جدارات 🏛️",
            })
    except Exception:
        pass
    return jobs


# ─────────────────────────────────────────────
#  تجميع + تصفية
# ─────────────────────────────────────────────

def collect_jobs() -> list:
    all_jobs = []

    # جدارات أولاً (حكومي)
    print("  🏛️  جدارات...")
    all_jobs.extend(fetch_jadarat())
    time.sleep(0.5)

    # باقي المصادر مع كلمات مختلفة
    sources = [fetch_indeed, fetch_bayt, fetch_linkedin]
    # نأخذ 4 كلمات بحث متنوعة لتقليل الطلبات
    selected_keywords = random.sample(KEYWORDS, min(4, len(KEYWORDS)))

    for kw in selected_keywords:
        for fn in sources:
            name = fn.__name__.replace("fetch_", "").capitalize()
            print(f"  🔍 {name} ← {kw}")
            results = fn(kw)
            all_jobs.extend(results)
            time.sleep(random.uniform(0.8, 1.5))

    # إزالة التكرار بالعنوان
    seen, unique = set(), []
    for job in all_jobs:
        key = job["title"].lower().strip()[:60]
        if key and key not in seen:
            seen.add(key)
            unique.append(job)

    return unique


# ─────────────────────────────────────────────
#  توليد الإيميل
# ─────────────────────────────────────────────

def build_email(jobs: list) -> tuple[str, str, str]:
    """Returns (subject, html_body, plain_text)"""
    today_ar = datetime.now().strftime("%d/%m/%Y")
    today_en = datetime.now().strftime("%Y%m%d")

    subject = f"🤖 وظايف التقنية والذكاء الاصطناعي في السعودية – {today_ar}"

    # تجميع حسب المصدر
    by_source: dict[str, list] = {}
    for job in jobs:
        by_source.setdefault(job["source"], []).append(job)

    # ───── HTML ─────
    cards_html = ""
    for source, src_jobs in by_source.items():
        cards_html += f"""
        <tr><td style="padding:20px 30px 5px">
          <div style="font-size:13px;background:#e8f4fd;color:#1565c0;
                      display:inline-block;padding:3px 12px;border-radius:20px;
                      margin-bottom:12px">
            {source}
          </div>
        </td></tr>"""
        for job in src_jobs:
            btn = (
                f'<a href="{job["link"]}" '
                'style="display:inline-block;background:#1565c0;color:#fff;'
                'padding:8px 20px;border-radius:6px;text-decoration:none;'
                'font-size:13px;margin-top:8px">تقدم الآن ←</a>'
                if job["link"] else ""
            )
            cards_html += f"""
        <tr><td style="padding:4px 30px">
          <div style="background:#f8f9fa;border-radius:8px;padding:14px 16px;
                      border-right:4px solid #1565c0">
            <div style="font-weight:bold;font-size:15px;color:#1a1a2e">
              {job["title"]}
            </div>
            <div style="color:#555;font-size:13px;margin-top:4px">
              🏢 {job["company"]}
            </div>
            {btn}
          </div>
        </td></tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:20px;background:#f0f2f5;
             font-family:Arial,Helvetica,sans-serif;direction:rtl">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center">
<table width="680" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:12px;overflow:hidden;
              box-shadow:0 2px 12px rgba(0,0,0,.1)">

  <!-- HEADER -->
  <tr><td style="background:linear-gradient(135deg,#1a1a2e,#0d47a1);
                 padding:32px;text-align:center;color:#fff">
    <div style="font-size:28px;margin-bottom:8px">🤖</div>
    <div style="font-size:20px;font-weight:bold">وظايف التقنية والذكاء الاصطناعي</div>
    <div style="font-size:13px;opacity:.8;margin-top:6px">
      المملكة العربية السعودية &nbsp;•&nbsp; {today_ar}
    </div>
  </td></tr>

  <!-- STATS -->
  <tr><td style="padding:24px 30px 10px">
    <table width="100%"><tr>
      <td style="background:#e8f4fd;border-radius:8px;padding:14px;text-align:center;width:48%">
        <div style="font-size:28px;font-weight:bold;color:#1565c0">{len(jobs)}</div>
        <div style="font-size:12px;color:#555;margin-top:4px">وظيفة جديدة</div>
      </td>
      <td width="4%"></td>
      <td style="background:#e8f4fd;border-radius:8px;padding:14px;text-align:center;width:48%">
        <div style="font-size:28px;font-weight:bold;color:#1565c0">{len(by_source)}</div>
        <div style="font-size:12px;color:#555;margin-top:4px">مصدر</div>
      </td>
    </tr></table>
  </td></tr>

  <!-- JOBS -->
  {cards_html}

  <!-- FOOTER -->
  <tr><td style="background:#f8f9fa;padding:20px 30px;
                 text-align:center;color:#999;font-size:12px;
                 border-top:1px solid #eee">
    <p style="margin:0">تم توليد هذا التقرير تلقائياً بتاريخ {today_ar}</p>
    <p style="margin:6px 0 0">
      المصادر: LinkedIn • Bayt.com • Indeed • جدارات
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""

    # ───── PLAIN TEXT ─────
    lines = [f"وظايف التقنية في السعودية – {today_ar}", "=" * 50]
    for source, src_jobs in by_source.items():
        lines.append(f"\n[ {source} ]")
        for job in src_jobs:
            lines.append(f"• {job['title']} — {job['company']}")
            if job["link"]:
                lines.append(f"  رابط: {job['link']}")
    plain = "\n".join(lines)

    return subject, html, plain


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

DEMO_JOBS = [
    {"title": "AI Engineer – NLP & LLMs", "company": "Saudi Aramco", "link": "https://www.linkedin.com/jobs/", "source": "LinkedIn"},
    {"title": "Machine Learning Engineer", "company": "STC Solutions", "link": "https://www.bayt.com/en/saudi-arabia/jobs/", "source": "Bayt.com"},
    {"title": "Data Scientist – Vision 2030 Projects", "company": "NEOM", "link": "https://www.bayt.com/en/saudi-arabia/jobs/", "source": "Bayt.com"},
    {"title": "Cloud & DevOps Engineer (AWS)", "company": "Elm Company", "link": "https://sa.indeed.com/jobs", "source": "Indeed 🇸🇦"},
    {"title": "Cybersecurity Analyst", "company": "Saudi National Bank", "link": "https://sa.indeed.com/jobs", "source": "Indeed 🇸🇦"},
    {"title": "RPA Developer – UiPath", "company": "Deloitte KSA", "link": "https://www.linkedin.com/jobs/", "source": "LinkedIn"},
    {"title": "Senior Python Developer", "company": "Mobily", "link": "https://www.linkedin.com/jobs/", "source": "LinkedIn"},
    {"title": "IT Project Manager", "company": "Ministry of Health", "link": "https://jadarat.sa", "source": "جدارات 🏛️"},
    {"title": "Data Engineer – Azure", "company": "PwC Saudi Arabia", "link": "https://www.bayt.com/en/saudi-arabia/jobs/", "source": "Bayt.com"},
    {"title": "AI Product Manager", "company": "STC", "link": "https://www.linkedin.com/jobs/", "source": "LinkedIn"},
]


def main():
    import sys
    demo_mode = "--demo" in sys.argv

    print("\n🚀 Saudi Tech Job Hunter – يبحث عن وظايف التقنية في السعودية\n")

    if demo_mode:
        print("📋 وضع تجريبي – يعرض نموذج الإيميل بدون اتصال إنترنت\n")
        jobs = DEMO_JOBS
    else:
        jobs = collect_jobs()

    if not jobs:
        print("⚠️  لم يتم العثور على وظايف – تحقق من الاتصال بالإنترنت.")
        print("💡 جرب: python3 job_hunter.py --demo  (لرؤية نموذج الإيميل)")
        return

    subject, html_body, plain_text = build_email(jobs)

    # حفظ الملفات
    today = datetime.now().strftime("%Y%m%d")
    out_dir = os.path.dirname(os.path.abspath(__file__))

    html_path  = os.path.join(out_dir, f"jobs_{today}.html")
    txt_path   = os.path.join(out_dir, f"jobs_{today}.txt")
    subj_path  = os.path.join(out_dir, "email_subject.txt")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_body)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(plain_text)
    with open(subj_path, "w", encoding="utf-8") as f:
        f.write(subject)

    print(f"\n✅ تم العثور على {len(jobs)} وظيفة\n")
    print("─" * 50)
    print(f"📌 موضوع الإيميل:\n   {subject}")
    print("─" * 50)
    print(f"📄 ملف HTML  : {html_path}")
    print(f"📝 ملف نصي  : {txt_path}")
    print("─" * 50)
    print("\n📧 طريقة الإرسال:")
    print("  1. افتح Gmail أو Outlook")
    print("  2. انسخ الموضوع من email_subject.txt")
    print(f"  3. افتح jobs_{today}.html في المتصفح وانسخ المحتوى")
    print("  4. الصق في جسم الإيميل وأرسل!\n")


if __name__ == "__main__":
    main()
