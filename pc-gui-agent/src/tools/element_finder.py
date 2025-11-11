"""
元素查找工具
"""
import json
import re
from typing import List, Dict, Any, Optional
from ..llm.ollama_client import OllamaClient
from ..llm.prompt_templates import get_element_finding_prompt
from .dom_analyzer import DOMAnalyzer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ElementFinder:
    """元素查找器"""
    
    def __init__(self, ollama_client: Optional[OllamaClient]):
        """
        初始化元素查找器
        
        Args:
            ollama_client: Ollama客户端（可选）
        """
        self.ollama_client = ollama_client
        self.dom_analyzer = DOMAnalyzer()
    
    async def find_element(
        self,
        page,
        action_description: str,
        element_type: str = "input"  # input, button, link等
    ) -> Optional[str]:
        """
        根据动作描述查找目标元素的选择器
        
        Args:
            page: Playwright页面对象
            action_description: 动作描述，如"输入搜索关键词"、"点击搜索按钮"
            element_type: 元素类型
            
        Returns:
            CSS选择器，如果找不到返回None
        """
        try:
            # 1. 提取页面可交互元素
            elements = await self.dom_analyzer.extract_interactive_elements(page)
            
            if not elements:
                logger.warning("No interactive elements found on page")
                return None
            
            # 2. 过滤出匹配类型的元素
            filtered_elements = [
                el for el in elements
                if self._matches_element_type(el, element_type)
            ]
            
            if not filtered_elements:
                logger.warning(f"No {element_type} elements found")
                # 如果没找到匹配类型的，使用所有元素
                filtered_elements = elements
            
            # 3. 格式化元素信息
            elements_text = self.dom_analyzer.format_elements_for_llm(filtered_elements)
            
            # 4. 使用LLM查找目标元素
            if not self.ollama_client:
                logger.warning("OllamaClient not available, cannot use LLM for element finding")
                # 尝试简单的文本匹配
                return await self.find_element_by_text(page, action_description, element_type)
            
            prompt = get_element_finding_prompt(
                action_description=action_description,
                element_type=element_type,
                available_elements=elements_text
            )
            
            response = await self.ollama_client.generate_async(prompt)
            
            # 5. 解析响应，提取选择器
            selector = self._parse_finding_response(response, filtered_elements)
            
            if selector:
                logger.info(f"Found element selector: {selector} for action: {action_description}")
            else:
                logger.warning(f"Could not find element for action: {action_description}")
            
            return selector
        
        except Exception as e:
            logger.error(f"Error finding element: {e}")
            return None
    
    def _matches_element_type(self, element: Dict[str, Any], element_type: str) -> bool:
        """
        判断元素是否匹配指定类型
        
        Args:
            element: 元素信息
            element_type: 目标类型
            
        Returns:
            是否匹配
        """
        tag = element.get('tag', '').lower()
        el_type = element.get('type', '').lower()
        
        if element_type == 'input':
            return tag == 'input' and el_type in ['text', 'search', 'email', 'password', '']
        elif element_type == 'button':
            return tag == 'button' or el_type == 'button' or 'button' in element.get('className', '').lower()
        elif element_type == 'link':
            return tag == 'a'
        else:
            return tag == element_type
    
    def _parse_finding_response(
        self,
        response: str,
        elements: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        解析LLM响应，提取选择器
        
        Args:
            response: LLM响应
            elements: 可用元素列表
            
        Returns:
            CSS选择器
        """
        try:
            # 尝试提取JSON
            response = response.strip()
            
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            
            # 尝试解析JSON
            try:
                result = json.loads(response)
                selector = result.get('selector') or result.get('css_selector')
                if selector:
                    return selector
            except json.JSONDecodeError:
                pass
            
            # 如果JSON解析失败，尝试直接提取选择器（可能是纯文本）
            # 查找类似 "#id" 或 ".class" 或 "input[type='text']" 的模式
            patterns = [
                r'#[\w-]+',  # ID选择器
                r'\.[\w-]+',  # 类选择器
                r'input\[[^\]]+\]',  # 属性选择器
                r'button[^\s]*',  # button标签
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response)
                if match:
                    selector = match.group(0)
                    # 验证选择器是否在元素列表中
                    if any(el['selector'] == selector or selector in el['selector'] for el in elements):
                        return selector
            
            # 如果还是找不到，尝试从元素列表中匹配文本
            # 查找响应中提到的元素序号
            number_match = re.search(r'(\d+)', response)
            if number_match:
                index = int(number_match.group(1)) - 1
                if 0 <= index < len(elements):
                    return elements[index]['selector']
            
            return None
        
        except Exception as e:
            logger.error(f"Error parsing finding response: {e}")
            return None
    
    async def find_element_by_text(
        self,
        page,
        text: str,
        element_type: str = "button"
    ) -> Optional[str]:
        """
        根据文本内容查找元素（简单匹配）
        
        Args:
            page: Playwright页面对象
            text: 文本内容
            element_type: 元素类型
            
        Returns:
            CSS选择器
        """
        try:
            elements = await self.dom_analyzer.extract_interactive_elements(page)
            
            for el in elements:
                if self._matches_element_type(el, element_type):
                    el_text = el.get('text', '').lower()
                    placeholder = el.get('placeholder', '').lower()
                    search_text = text.lower()
                    
                    if search_text in el_text or search_text in placeholder:
                        return el['selector']
            
            return None
        
        except Exception as e:
            logger.error(f"Error finding element by text: {e}")
            return None

