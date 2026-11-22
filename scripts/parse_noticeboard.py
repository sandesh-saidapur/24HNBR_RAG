import urllib.request
import re

url = 'https://www.24h-information.de/index.php?id=5607&jahr=2026&uid=5609'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        
    print(f"HTML length: {len(html)}")
    # Find all links
    links = re.findall(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
    print(f"Total links found: {len(links)}")
    print("All links:")
    for href, text in links[:25]:
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        print(f"  {href} -> {clean_text}")
        
    # Check what is inside the main div or text
    main_text = re.sub(r'<[^>]+>', ' ', html)
    main_text = ' '.join(main_text.split())
    print("\nPage text excerpt:")
    print(main_text[:1000])
except Exception as e:
    print(f"Error: {e}")
