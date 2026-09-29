#!/usr/bin/env python3
"""
豆包视频分享链接解析器
使用Playwright解析视频直链
"""
import json
import sys
import time
from playwright.sync_api import sync_playwright

def extract_video_url(share_url, timeout=30):
    """从豆包视频分享链接提取视频直链"""
    result = {
        "success": False,
        "share_url": share_url,
        "video_url": None,
        "title": None,
        "metadata": {},
        "error": None
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path='/usr/local/bin/chromium-browser',
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN'
        )
        
        page = context.new_page()
        
        # 监听网络请求，捕获视频请求
        video_requests = []
        def handle_request(request):
            url = request.url
            if any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.ts', 'video', 'media']):
                if 'doubao' in url or 'bytecdn' in url or 'bytedance' in url or 'volccdn' in url:
                    video_requests.append({
                        'url': url,
                        'method': request.method,
                        'resource_type': request.resource_type
                    })
        
        page.on('request', handle_request)
        
        try:
            print(f"[1/4] 正在打开页面: {share_url}")
            page.goto(share_url, wait_until='domcontentloaded', timeout=timeout*1000)
            
            print("[2/4] 等待页面加载和视频初始化...")
            time.sleep(5)
            
            # 尝试点击播放按钮
            try:
                play_button = page.query_selector('button[class*="play"], .play-btn, [class*="PlayButton"]')
                if play_button:
                    print("[3/4] 检测到播放按钮，点击播放...")
                    play_button.click()
                    time.sleep(3)
            except Exception as e:
                print(f"[3/4] 未找到播放按钮或点击失败: {e}")
            
            # 等待更多时间让视频加载
            time.sleep(3)
            
            # 方法1: 从video标签提取src
            print("[4/4] 提取视频信息...")
            video_elements = page.query_selector_all('video')
            for i, video in enumerate(video_elements):
                src = video.get_attribute('src')
                current_src = video.evaluate('el => el.currentSrc')
                print(f"  video[{i}]: src={src}, currentSrc={current_src}")
                if src and src.startswith('http'):
                    result['video_url'] = src
                    break
                if current_src and current_src.startswith('http'):
                    result['video_url'] = current_src
                    break
            
            # 方法2: 从捕获的网络请求中提取
            if not result['video_url'] and video_requests:
                print(f"  从网络请求中提取，共捕获 {len(video_requests)} 个视频请求")
                for req in video_requests:
                    print(f"    - {req['url'][:100]}...")
                # 选择第一个mp4或m3u8链接
                for req in video_requests:
                    if '.mp4' in req['url'].lower() or '.m3u8' in req['url'].lower():
                        result['video_url'] = req['url']
                        break
                if not result['video_url'] and video_requests:
                    result['video_url'] = video_requests[0]['url']
            
            # 方法3: 从页面JavaScript变量中提取
            if not result['video_url']:
                try:
                    # 尝试获取页面中的视频相关数据
                    page_data = page.evaluate('''() => {
                        const data = {};
                        // 检查常见的全局变量
                        if (window.__INITIAL_STATE__) data.initialState = window.__INITIAL_STATE__;
                        if (window.__NEXT_DATA__) data.nextData = window.__NEXT_DATA__;
                        if (window.videoData) data.videoData = window.videoData;
                        // 获取所有meta标签
                        data.metas = Array.from(document.querySelectorAll('meta')).map(m => ({
                            property: m.getAttribute('property'),
                            content: m.getAttribute('content')
                        })).filter(m => m.content && (m.property || '').includes('video'));
                        return data;
                    }''')
                    
                    if page_data.get('metas'):
                        for meta in page_data['metas']:
                            print(f"  meta: {meta['property']} = {meta['content']}")
                            if meta['content'] and ('.mp4' in meta['content'].lower() or 'video' in (meta['property'] or '').lower()):
                                if meta['content'].startswith('http'):
                                    result['video_url'] = meta['content']
                                    break
                    
                    result['metadata']['page_data'] = str(page_data)[:500]
                except Exception as e:
                    print(f"  从JS变量提取失败: {e}")
            
            # 提取页面标题
            result['title'] = page.title()
            
            # 截图保存用于调试
            page.screenshot(path='/home/user/Doubao/chats/38439832899843586/video_page_screenshot.png', full_page=True)
            print(f"  页面截图已保存: video_page_screenshot.png")
            
            if result['video_url']:
                result['success'] = True
                print(f"\n✅ 成功提取视频直链:")
                print(f"   标题: {result['title']}")
                print(f"   视频URL: {result['video_url']}")
            else:
                result['error'] = "未能从页面中提取到视频直链"
                print(f"\n❌ 提取失败: {result['error']}")
                print(f"   捕获的视频请求数: {len(video_requests)}")
                if video_requests:
                    print("   捕获的请求:")
                    for req in video_requests:
                        print(f"     - {req['url'][:150]}")
                
        except Exception as e:
            result['error'] = str(e)
            print(f"\n❌ 解析出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()
    
    return result

if __name__ == '__main__':
    share_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.doubao.com/video-sharing?source_type=mobile&share_id=55308757968764418&video_id=v0269cg10004daja0da7dld2h7qrt1n0"
    
    result = extract_video_url(share_url)
    
    # 保存结果到JSON
    output_path = '/home/user/Doubao/chats/38439832899843586/video_extract_result.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {output_path}")
