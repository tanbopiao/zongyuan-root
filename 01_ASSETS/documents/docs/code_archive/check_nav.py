import urllib.request, re, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

html = urllib.request.urlopen("https://www.huodouai.com/", timeout=5, context=ctx).read().decode()
links = re.findall(r'href="(/[^"]*)"', html)
links = list(dict.fromkeys(links))

print("官网导航链接总数:", len(links))
print()
ok = 0
fail = 0
fail_list = []
for link in links:
    if link.startswith("//") or link.startswith("http"):
        continue
    url = "https://www.huodouai.com" + link
    try:
        req = urllib.request.Request(url, method="HEAD")
        code = urllib.request.urlopen(req, timeout=5, context=ctx).status
        if code == 200:
            ok += 1
        else:
            fail += 1
            fail_list.append((code, link))
    except Exception as e:
        fail += 1
        fail_list.append(("ERR", link))

print("可访问:", ok)
print("不可访问:", fail)
if fail_list:
    print("\n不可访问列表:")
    for code, link in fail_list:
        print(" ", code, link)
