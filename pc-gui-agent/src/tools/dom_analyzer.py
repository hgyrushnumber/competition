"""
DOM分析工具
"""
from typing import List, Dict, Any, Optional
from playwright.async_api import Page
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DOMAnalyzer:
    """DOM分析器"""
    
    @staticmethod
    async def extract_interactive_elements(page: Page) -> List[Dict[str, Any]]:
        """
        提取页面中的可交互元素
        
        Args:
            page: Playwright页面对象
            
        Returns:
            元素列表，每个元素包含：tag, type, id, class, text, selector等信息
        """
        try:
            # 提取关键可交互元素，优先识别搜索框等关键元素
            elements = await page.evaluate("""
                () => {
                    const elements = [];
                    const selectors = [
                        'input[type="text"]',
                        'input[type="search"]',
                        'input[type="email"]',
                        'input[type="password"]',
                        'textarea',
                        'button',
                        'a[href]',
                        '[role="button"]',
                        '[onclick]'
                    ];
                    
                    // 优先选择器（搜索框常见特征）
                    const prioritySelectors = [
                        'input[name="wd"]',  // 百度搜索框
                        'input#kw',  // 百度搜索框ID
                        'input[name="q"]',  // Google搜索框
                        'input[placeholder*="搜索"]',
                        'input[placeholder*="search"]',
                        'input[type="search"]'
                    ];
                    
                    // 先提取优先元素
                    prioritySelectors.forEach(selector => {
                        try {
                            document.querySelectorAll(selector).forEach(el => {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    let uniqueSelector = selector;
                                    if (el.id) {
                                        uniqueSelector = `#${el.id}`;
                                    } else if (el.name) {
                                        uniqueSelector = `input[name="${el.name}"]`;
                                    }
                                    
                                    elements.push({
                                        tag: el.tagName.toLowerCase(),
                                        type: el.type || el.getAttribute('type') || '',
                                        id: el.id || '',
                                        className: el.className || '',
                                        name: el.name || '',
                                        placeholder: el.placeholder || '',
                                        text: el.textContent?.trim().substring(0, 50) || el.value?.substring(0, 50) || '',
                                        selector: uniqueSelector,
                                        priority: true,  // 标记为优先元素
                                        visible: true,
                                        position: {
                                            x: Math.round(rect.x),
                                            y: Math.round(rect.y),
                                            width: Math.round(rect.width),
                                            height: Math.round(rect.height)
                                        }
                                    });
                                }
                            });
                        } catch (e) {
                            // 忽略选择器错误
                        }
                    });
                    
                    // 再提取其他元素
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach((el, index) => {
                            // 跳过已经添加的优先元素
                            const alreadyAdded = elements.some(e => 
                                e.id === el.id || 
                                (e.name && e.name === el.name) ||
                                e.selector === `#${el.id}`
                            );
                            if (alreadyAdded) return;
                            
                            // 生成唯一选择器，优先使用ID和name
                            let uniqueSelector = selector;
                            if (el.id) {
                                uniqueSelector = `#${el.id}`;
                            } else if (el.name) {
                                uniqueSelector = `${el.tagName.toLowerCase()}[name="${el.name}"]`;
                            } else if (el.className && typeof el.className === 'string') {
                                const classes = el.className.split(' ').filter(c => c);
                                if (classes.length > 0) {
                                    uniqueSelector = `${selector}.${classes[0]}`;
                                }
                            }
                            
                            // 如果还是不够唯一，添加nth-child
                            const allMatches = document.querySelectorAll(selector);
                            if (allMatches.length > 1 && !el.id && !el.name) {
                                const parent = el.parentElement;
                                if (parent) {
                                    const siblings = Array.from(parent.children);
                                    const index = siblings.indexOf(el);
                                    uniqueSelector = `${uniqueSelector}:nth-child(${index + 1})`;
                                }
                            }
                            
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {  // 只包含可见元素
                                elements.push({
                                    tag: el.tagName.toLowerCase(),
                                    type: el.type || el.getAttribute('type') || '',
                                    id: el.id || '',
                                    className: el.className || '',
                                    name: el.name || '',
                                    placeholder: el.placeholder || '',
                                    text: el.textContent?.trim().substring(0, 50) || el.value?.substring(0, 50) || '',
                                    selector: uniqueSelector,
                                    priority: false,
                                    visible: rect.width > 0 && rect.height > 0,
                                    position: {
                                        x: Math.round(rect.x),
                                        y: Math.round(rect.y),
                                        width: Math.round(rect.width),
                                        height: Math.round(rect.height)
                                    }
                                });
                            }
                        });
                    });
                    
                    // 按优先级排序（优先元素在前）
                    elements.sort((a, b) => {
                        if (a.priority && !b.priority) return -1;
                        if (!a.priority && b.priority) return 1;
                        return 0;
                    });
                    
                    return elements;
                }
            """)
            
            logger.info(f"Extracted {len(elements)} interactive elements")
            return elements
        
        except Exception as e:
            logger.error(f"Error extracting DOM elements: {e}")
            return []
    
    @staticmethod
    async def extract_page_structure(page: Page, max_depth: int = 3) -> Dict[str, Any]:
        """
        提取页面结构（简化版）
        
        Args:
            page: Playwright页面对象
            max_depth: 最大深度
            
        Returns:
            页面结构信息
        """
        try:
            structure = await page.evaluate(f"""
                (maxDepth) => {{
                    function extractStructure(element, depth) {{
                        if (depth > maxDepth) return null;
                        
                        const rect = element.getBoundingClientRect();
                        const isVisible = rect.width > 0 && rect.height > 0;
                        
                        if (!isVisible) return null;
                        
                        const info = {{
                            tag: element.tagName.toLowerCase(),
                            id: element.id || '',
                            className: element.className || '',
                            text: element.textContent?.trim().substring(0, 100) || '',
                            children: []
                        }};
                        
                        if (depth < maxDepth) {{
                            Array.from(element.children).forEach(child => {{
                                const childInfo = extractStructure(child, depth + 1);
                                if (childInfo) {{
                                    info.children.push(childInfo);
                                }}
                            }});
                        }}
                        
                        return info;
                    }}
                    
                    return extractStructure(document.body, 0);
                }}
            """, max_depth)
            
            return structure or {}
        
        except Exception as e:
            logger.error(f"Error extracting page structure: {e}")
            return {}
    
    @staticmethod
    async def get_element_info(page: Page, selector: str) -> Optional[Dict[str, Any]]:
        """
        获取特定元素的信息
        
        Args:
            page: Playwright页面对象
            selector: 元素选择器
            
        Returns:
            元素信息
        """
        try:
            element_info = await page.evaluate(f"""
                (selector) => {{
                    const el = document.querySelector(selector);
                    if (!el) return null;
                    
                    const rect = el.getBoundingClientRect();
                    return {{
                        tag: el.tagName.toLowerCase(),
                        type: el.type || el.getAttribute('type') || '',
                        id: el.id || '',
                        className: el.className || '',
                        name: el.name || '',
                        placeholder: el.placeholder || '',
                        text: el.textContent?.trim().substring(0, 100) || el.value?.substring(0, 100) || '',
                        visible: rect.width > 0 && rect.height > 0,
                        position: {{
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        }}
                    }};
                }}
            """, selector)
            
            return element_info
        
        except Exception as e:
            logger.error(f"Error getting element info: {e}")
            return None
    
    @staticmethod
    def format_elements_for_llm(elements: List[Dict[str, Any]]) -> str:
        """
        格式化元素列表为LLM可理解的文本
        
        Args:
            elements: 元素列表
            
        Returns:
            格式化后的文本
        """
        if not elements:
            return "页面中没有找到可交互元素"
        
        lines = []
        for i, el in enumerate(elements, 1):
            desc_parts = []
            
            # 标记优先元素
            priority_mark = "⭐" if el.get('priority') else ""
            
            if el.get('text'):
                desc_parts.append(f"文本: {el['text']}")
            if el.get('placeholder'):
                desc_parts.append(f"占位符: {el['placeholder']}")
            if el.get('id'):
                desc_parts.append(f"ID: {el['id']}")
            if el.get('name'):
                desc_parts.append(f"name: {el['name']}")
            if el.get('className'):
                desc_parts.append(f"类: {el['className']}")
            
            desc = " | ".join(desc_parts) if desc_parts else "无描述"
            
            lines.append(
                f"{i}. {priority_mark} {el['tag']} ({el['type'] or 'N/A'}) - {desc} - 选择器: {el['selector']}"
            )
        
        return "\n".join(lines)

