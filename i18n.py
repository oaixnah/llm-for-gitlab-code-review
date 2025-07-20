import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class I18n:
    """国际化管理类"""

    def __init__(self, default_locale: str = 'zh_CN'):
        self.default_locale = default_locale
        self.current_locale = default_locale
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.locales_dir = Path(__file__).parent / 'locales'
        self._load_translations()

    def _load_translations(self):
        """加载翻译文件"""
        if not self.locales_dir.exists():
            self.locales_dir.mkdir(exist_ok=True)
            return

        for locale_file in self.locales_dir.glob('*.json'):
            locale = locale_file.stem
            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self.translations[locale] = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load locale file {locale_file}: {e}")

    def set_locale(self, locale: str):
        """设置当前语言"""
        if locale in self.translations or locale == self.default_locale:
            self.current_locale = locale
        else:
            print(f"Warning: Locale '{locale}' not found, using default '{self.default_locale}'")

    def get_locale(self) -> str:
        """获取当前语言"""
        return self.current_locale

    def t(self, key: str, **kwargs) -> str:
        """翻译文本
        
        Args:
            key: 翻译键，支持点号分隔的嵌套键
            **kwargs: 模板变量
        
        Returns:
            翻译后的文本
        """
        # 获取翻译文本
        text = self._get_translation(key)

        # 如果有模板变量，进行替换
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text

        return text

    def _get_translation(self, key: str) -> str:
        """获取翻译文本"""
        # 尝试从当前语言获取
        text = self._get_nested_value(self.translations.get(self.current_locale, {}), key)

        # 如果当前语言没有，尝试从默认语言获取
        if text is None and self.current_locale != self.default_locale:
            text = self._get_nested_value(self.translations.get(self.default_locale, {}), key)

        # 如果都没有，返回键本身
        return text if text is not None else key

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[str]:
        """获取嵌套字典的值"""
        keys = key.split('.')
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current if isinstance(current, str) else None

    def get_available_locales(self) -> list:
        """获取可用的语言列表"""
        return list(self.translations.keys())


# 全局实例
i18n = I18n()


def get_locale_from_env() -> str:
    """从环境变量获取语言设置"""
    return os.getenv('LOCALE', os.getenv('LANG', 'zh_CN')).split('.')[0].replace('-', '_')


def init_i18n():
    """初始化国际化"""
    locale = get_locale_from_env()
    i18n.set_locale(locale)
