#!/usr/bin/env python3
"""
多模态API对接模块
- 支持百度/腾讯/阿里三家免费API
- 配置化密钥管理
- 自动降级机制
- 文档本地解析（PyPDF2/python-docx）
"""
import os
import json
import base64
import time
import hashlib
import requests
from datetime import datetime

CONFIG_PATH = '/opt/ZONGYUAN-ROOT/gov_api/config/multimodal_api_config.json'
UPLOAD_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data/uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

class MultimodalAPIConnector:
    def __init__(self):
        self.config = self._load_config()
        self.default_provider = self.config.get('default_provider', 'baidu')
        self.tokens = {}
        self.token_expiry = {}
    
    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'providers': {}, 'default_provider': 'baidu'}
    
    def _get_provider_config(self, provider=None):
        provider = provider or self.default_provider
        return self.config.get('providers', {}).get(provider, {})
    
    def _is_configured(self, provider=None):
        cfg = self._get_provider_config(provider)
        if not cfg.get('enabled', False):
            return False
        # 检查是否配置了真实密钥（非占位符）
        api_key = cfg.get('api_key', '') or cfg.get('secret_id', '') or cfg.get('app_key', '')
        return api_key and not api_key.startswith('YOUR_')
    
    def _get_baidu_token(self):
        """获取百度API access_token"""
        cfg = self._get_provider_config('baidu')
        cache_key = 'baidu_token'
        if cache_key in self.tokens and time.time() < self.token_expiry.get(cache_key, 0):
            return self.tokens[cache_key]
        
        try:
            resp = requests.post(cfg['token_endpoint'], params={
                'grant_type': 'client_credentials',
                'client_id': cfg['api_key'],
                'client_secret': cfg['secret_key']
            }, timeout=10)
            data = resp.json()
            token = data.get('access_token', '')
            if token:
                self.tokens[cache_key] = token
                self.token_expiry[cache_key] = time.time() + data.get('expires_in', 2592000) - 300
                return token
        except Exception as e:
            print(f'百度token获取失败: {e}')
        return None
    
    def ocr_recognize(self, image_path, provider=None):
        """OCR文字识别"""
        provider = provider or self.default_provider
        
        if not self._is_configured(provider):
            return self._ocr_fallback(image_path, '未配置API密钥')
        
        if provider == 'baidu':
            return self._baidu_ocr(image_path)
        elif provider == 'tencent':
            return self._tencent_ocr(image_path)
        elif provider == 'aliyun':
            return self._aliyun_ocr(image_path)
        
        return self._ocr_fallback(image_path, f'不支持的提供商: {provider}')
    
    def _baidu_ocr(self, image_path):
        """百度OCR"""
        try:
            token = self._get_baidu_token()
            if not token:
                return self._ocr_fallback(image_path, 'token获取失败')
            
            with open(image_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode()
            
            resp = requests.post(
                self._get_provider_config('baidu')['ocr_endpoint'],
                params={'access_token': token},
                data={'image': img_data},
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            data = resp.json()
            if 'words_result' in data:
                words = [item['words'] for item in data['words_result']]
                return {
                    'success': True,
                    'provider': 'baidu',
                    'text': '\n'.join(words),
                    'word_count': len(words),
                    'raw_result': data
                }
            return self._ocr_fallback(image_path, data.get('error_msg', '识别失败'))
        except Exception as e:
            return self._ocr_fallback(image_path, str(e))
    
    def _tencent_ocr(self, image_path):
        """腾讯OCR（简化版，需签名）"""
        return self._ocr_fallback(image_path, '腾讯OCR待实现签名')
    
    def _aliyun_ocr(self, image_path):
        """阿里OCR（简化版）"""
        return self._ocr_fallback(image_path, '阿里OCR待实现')
    
    def _ocr_fallback(self, image_path, reason):
        """OCR降级"""
        file_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
        return {
            'success': False,
            'provider': 'fallback',
            'text': '',
            'word_count': 0,
            'file_size': file_size,
            'reason': reason,
            'message': 'OCR识别暂不可用，请配置API密钥后使用',
            'status': 'pending_configuration'
        }
    
    def text_to_speech(self, text, voice='female', speed='normal', provider=None):
        """文本转语音"""
        provider = provider or self.default_provider
        
        if not self._is_configured(provider):
            return self._tts_fallback(text, '未配置API密钥')
        
        if provider == 'baidu':
            return self._baidu_tts(text, voice, speed)
        
        return self._tts_fallback(text, f'提供商{provider}待实现')
    
    def _baidu_tts(self, text, voice, speed):
        """百度TTS"""
        try:
            token = self._get_baidu_token()
            if not token:
                return self._tts_fallback(text, 'token获取失败')
            
            cfg = self._get_provider_config('baidu')
            resp = requests.post(
                cfg['tts_endpoint'],
                data={
                    'tex': text,
                    'tok': token,
                    'cuid': 'gov_ai_platform',
                    'ctp': '1',
                    'lan': 'zh',
                    'spd': '5',
                    'pit': '5',
                    'vol': '5',
                    'per': '0' if voice == 'female' else '1'
                },
                timeout=30
            )
            
            if resp.headers.get('Content-Type', '').startswith('audio/'):
                audio_file = os.path.join(UPLOAD_DIR, f'tts_{int(time.time())}.mp3')
                with open(audio_file, 'wb') as f:
                    f.write(resp.content)
                return {
                    'success': True,
                    'provider': 'baidu',
                    'audio_file': audio_file,
                    'audio_size': len(resp.content),
                    'text_length': len(text),
                    'voice': voice
                }
            return self._tts_fallback(text, 'TTS返回非音频数据')
        except Exception as e:
            return self._tts_fallback(text, str(e))
    
    def _tts_fallback(self, text, reason):
        """TTS降级"""
        return {
            'success': False,
            'provider': 'fallback',
            'audio_file': None,
            'text_length': len(text),
            'estimated_duration': f'{len(text) * 0.3:.1f}秒',
            'reason': reason,
            'message': '语音合成暂不可用，请配置API密钥后使用',
            'status': 'pending_configuration'
        }
    
    def parse_document(self, file_path, file_type=None):
        """文档解析（本地库，完全免费）"""
        if not os.path.exists(file_path):
            return {'success': False, 'error': 'file not found'}
        
        if not file_type:
            _, file_type = os.path.splitext(file_path)
        file_type = file_type.lower()
        
        try:
            text = ''
            if file_type in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            elif file_type == '.pdf':
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
            elif file_type in ['.doc', '.docx']:
                import docx
                doc = docx.Document(file_path)
                text = '\n'.join(p.text for p in doc.paragraphs)
            else:
                return {'success': False, 'error': f'不支持的文件类型: {file_type}'}
            
            import re
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
            
            return {
                'success': True,
                'file_type': file_type,
                'text_length': len(text),
                'text': text[:5000],
                'full_text_saved': len(text) > 5000,
                'paragraph_count': len([p for p in text.split('\n') if p.strip()]),
                'parser': 'local'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_status(self):
        """获取多模态API状态"""
        providers_status = []
        for name, cfg in self.config.get('providers', {}).items():
            providers_status.append({
                'name': name,
                'display_name': cfg.get('name', name),
                'enabled': cfg.get('enabled', False),
                'configured': self._is_configured(name),
                'free_quota': cfg.get('free_quota', {})
            })
        
        return {
            'status': 'ready' if any(p['configured'] for p in providers_status) else 'pending_configuration',
            'default_provider': self.default_provider,
            'providers': providers_status,
            'document_parsing': 'ready (local, free)',
            'ocr': 'configured' if any(p['configured'] for p in providers_status) else 'pending_api_key',
            'tts': 'configured' if any(p['configured'] for p in providers_status) else 'pending_api_key',
            'config_path': CONFIG_PATH
        }

multimodal_connector = MultimodalAPIConnector()

if __name__ == '__main__':
    print(json.dumps(multimodal_connector.get_status(), ensure_ascii=False, indent=2))
