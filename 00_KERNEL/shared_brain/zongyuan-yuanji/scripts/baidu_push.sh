#!/bin/bash
URLS="https://www.huodouai.com/
https://www.huodouai.com/pipeline.html
https://www.huodouai.com/products.html
https://www.huodouai.com/kernel.html
https://www.huodouai.com/gov.html
https://www.huodouai.com/status.html
https://www.huodouai.com/chat.html
https://www.huodouai.com/kunlun/workbench.html
https://www.huodouai.com/kunlun/gallery.html"
echo "$URLS" | curl -sS -H "Content-Type:text/plain" --data-binary @- "http://data.zz.baidu.com/urls?site=https://www.huodouai.com&token=ke9znqkvnIcIIgPs"
