import asyncio
import sys
from playwright.sync_api import sync_playwright, Page, Error
from typing import Dict, Any, List, Protocol, Tuple


# 定义接口协议，便于依赖注入和模拟
class BrowserLauncher(Protocol):
    def launch(self, headless: bool = True):
        ...


class PlaywrightContextManager(Protocol):
    def __enter__(self):
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        ...


# 默认的 Playwright 实现
class DefaultPlaywrightManager:
    def __enter__(self):
        # 在 Windows 上设置正确的事件循环策略以避免 NotImplementedError
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                # 如果设置失败，尝试使用默认策略
                pass
        
        self._playwright_context = sync_playwright()
        self._playwright = self._playwright_context.__enter__()
        return self._playwright

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._playwright_context.__exit__(exc_type, exc_val, exc_tb)


class SandboxService:
    def __init__(self, playwright_manager=None, headless=True):
        """
        初始化沙箱服务

        Args:
            playwright_manager: Playwright 上下文管理器，用于依赖注入
            headless: 是否以无头模式运行浏览器
        """
        self._playwright_manager = playwright_manager or DefaultPlaywrightManager()
        self._headless = headless

    def run_evaluation(self, user_code: Dict[str, str], checkpoints: List[Dict[str, Any]], topic_id: str = None) -> Dict[str, Any]:
        """
        运行代码评测

        Args:
            user_code: 用户提交的代码，包含 html, css, js
            checkpoints: 检查点列表
            topic_id: 测试任务ID，用于判断是否使用 raw HTML 模式

        Returns:
            评测结果字典
        """
        # 根据 topic_id 判断是否使用 raw HTML 模式
        # 指定需要使用 raw HTML 模式的任务列表
        RAW_HTML_TASKS = ["1_3","1_end","2_end","3_end","4_end","5_end","6_end"]  # 可以在这里添加更多需要 raw 模式的任务
        raw_html_mode = (topic_id in RAW_HTML_TASKS)
        
        results = []
        passed_all = True

        browser = None
        page = None
        try:
            with self._playwright_manager as p:
                browser = p.chromium.launch(
                    headless=self._headless,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu'
                    ]
                )
                page = browser.new_page()

                # 根据模式构建HTML结构
                if raw_html_mode:
                    # Raw HTML模式：直接使用用户的完整HTML代码，不做任何修改
                    full_html = user_code.get('html', '')
                    
                    # 如果用户没有写任何内容，添加一个标记以便检查点识别
                    if not full_html.strip():
                        # 用户什么都没写，使用一个特殊的空页面
                        full_html = '<html><head></head><body data-empty="true"></body></html>'
                    
                    # 在Raw模式下，需要将CSS和JS也整合到HTML中
                    css_content = user_code.get('css', '')
                    js_content = user_code.get('js', '')
                    
                    # 将用户原始HTML传递给页面，供检查点使用
                    full_html_with_script = full_html + f'<script>window.userOriginalHTML = {repr(user_code.get("html", ""))}</script>'
                    
                    # 注入CSS和JS
                    if css_content:
                        # 在<head>标签中添加<style>标签
                        if '<head>' in full_html_with_script:
                            full_html_with_script = full_html_with_script.replace(
                                '<head>', 
                                f'<head><style>{css_content}</style>', 
                                1
                            )
                        else:
                            # 如果没有<head>标签，添加一个
                            full_html_with_script = full_html_with_script.replace(
                                '<html', 
                                f'<html><head><style>{css_content}</style></head>', 
                                1
                            )
                    
                    if js_content:
                        # 在</body>标签前添加<script>标签
                        if '</body>' in full_html_with_script:
                            full_html_with_script = full_html_with_script.replace(
                                '</body>', 
                                f'<script>{js_content}</script></body>', 
                                1
                            )
                        else:
                            # 如果没有</body>标签，添加一个
                            full_html_with_script = full_html_with_script + f'<script>{js_content}</script>'
                    
                    # 在Raw模式下也需要设置页面内容
                    page.set_content(full_html_with_script, wait_until="load")  # 等待页面加载完成
                else:
                    # 标准沙箱模式：将用户代码嵌入到标准模板中
                    # 检查用户代码是否已经包含完整的HTML结构
                    user_html = user_code.get('html', '')
                    if (user_html.strip().startswith('<!DOCTYPE html>') or 
                        user_html.strip().startswith('<html') or
                        '<html' in user_html.lower()):
                        # 用户代码已经包含HTML结构，直接使用
                        full_html = user_html
                        
                        # 注入CSS和JS到现有HTML中
                        css_content = user_code.get('css', '')
                        js_content = user_code.get('js', '')
                        
                        # 如果有CSS内容，尝试添加到<head>中
                        if css_content:
                            if '<head>' in full_html:
                                # 确保只替换第一个<head>标签
                                head_pos = full_html.find('<head>')
                                head_end_pos = full_html.find('>', head_pos) + 1
                                full_html = full_html[:head_end_pos] + f'<style>{css_content}</style>' + full_html[head_end_pos:]
                            else:
                                # 如果没有<head>，尝试添加到<html>后
                                html_pos = full_html.find('<html')
                                html_end_pos = full_html.find('>', html_pos) + 1
                                full_html = full_html[:html_end_pos] + f'<head><style>{css_content}</style></head>' + full_html[html_end_pos:]
                        
                        # 如果有JS内容，尝试添加到</body>前或</html>前
                        if js_content or True:  # 总是添加alert拦截脚本
                            # 添加alert拦截脚本
                            alert_script = """\n<script>\nwindow.__alertMessages = [];\nwindow.alert = function (msg) {\n    window.__alertMessages.push(msg);\n};\n</script>"""
                            
                            js_to_inject = alert_script
                            if js_content:
                                js_to_inject += f'\n<script>{js_content}</script>'
                            
                            if '</body>' in full_html:
                                # 在</body>标签前插入JS
                                body_end_pos = full_html.rfind('</body>')
                                full_html = full_html[:body_end_pos] + js_to_inject + full_html[body_end_pos:]
                            elif '</html>' in full_html:
                                # 在</html>标签前插入JS
                                html_end_pos = full_html.rfind('</html>')
                                full_html = full_html[:html_end_pos] + js_to_inject + full_html[html_end_pos:]
                            else:
                                # 如果都没有，直接追加
                                full_html = full_html + js_to_inject
                    else:
                        # 用户代码不包含HTML结构，使用标准模板
                        full_html = f"""<!DOCTYPE html>
                                        <html>
                                        <head>
                                            <meta charset="UTF-8">
                                            <style>{user_code.get('css', '')}</style>
                                        </head>
                                        <body>
                                            {user_code.get('html', '')}
                                            <script>
                                            window.__alertMessages = [];
                                            window.alert = function (msg) {{
                                                window.__alertMessages.push(msg);
                                            }};
                                            </script>
                                            <script>{user_code.get('js', '')}</script>
                                        </body>
                                        </html>"""
                    page.set_content(full_html, wait_until="load")  # 等待页面加载完成

                for i, cp in enumerate(checkpoints):
                    passed, detail = self._evaluate_checkpoint(page, cp)
                    if not passed:
                        passed_all = False
                        # 如果检查点有自定义反馈，使用它，否则用默认的
                        feedback = cp.feedback if hasattr(cp, 'feedback') and cp.feedback else detail
                        results.append(f"检查点 {i + 1} 失败: {feedback}")

        except Error as e:
            return {"passed": False, "message": "评测服务发生内部错误。", "details": [str(e)]}
        finally:
            # 确保资源被正确释放
            if browser:
                try:
                    browser.close()
                except Error:
                    # 浏览器可能已经关闭，忽略错误
                    pass
        
        message = "恭喜！所有测试点都通过了！" if passed_all else "很遗憾，部分测试点未通过。"
        return {"passed": passed_all, "message": message, "details": results}

    def _evaluate_checkpoint(self, page: Page, checkpoint) -> Tuple[bool, str]:
        """
        评估单个检查点

        Args:
            page: Playwright 页面对象
            checkpoint: 检查点配置（Pydantic模型）

        Returns:
            (是否通过, 详细信息) 的元组
        """
        cp_type = checkpoint.type
        try:
            # 执行交互 (如果需要)
            if cp_type == "interaction_and_assert":
                action_type = checkpoint.action_type
                action_selector = checkpoint.action_selector
                action_value = checkpoint.action_value
                
                try:
                    # 根据不同的动作类型执行相应的操作
                    if action_type == "click":
                        page.locator(action_selector).click()
                    elif action_type == "type_text":
                        if action_value is not None:
                            page.locator(action_selector).fill(action_value)
                        else:
                            return False, "type_text 操作需要提供 action_value"
                    elif action_type == "hover":
                        page.locator(action_selector).hover()
                    elif action_type == "focus":
                        page.locator(action_selector).focus()
                    elif action_type == "blur":
                        # Playwright没有直接的blur方法，可以通过focus其他元素或使用evaluate来实现
                        page.locator(action_selector).evaluate("""element => {
                            element.blur();
                        }""")
                    elif action_type == "scroll":
                        # 滚动到元素可见位置
                        page.locator(action_selector).scroll_into_view_if_needed()
                    elif action_type == "wait":
                        # 等待指定时间（毫秒）
                        if action_value is not None:
                            page.wait_for_timeout(int(action_value))
                        else:
                            # 默认等待100毫秒
                            page.wait_for_timeout(100)
                    else:
                        return False, f"不支持的动作类型: {action_type}"
                except Exception as e:
                    return False, f"执行动作 '{action_type}' 时发生错误: {e}"

                # 交互后，对嵌套的断言进行评估
                return self._evaluate_assertion(page, checkpoint.assertion)
            else:
                # 如果不是交互式检查点，直接评估断言
                return self._evaluate_assertion(page, checkpoint)

        except Exception as e:
            return False, f"执行检查点时发生错误: {e}"

    def _evaluate_assertion(self, page: Page, assertion) -> Tuple[bool, str]:
        """
        专门处理各种非交互的断言的私有方法
        """
        if assertion is None:
            return True, "通过"
            
        assertion_type = assertion.type

        try:
            if assertion_type == "assert_style":
                selector = assertion.selector
                css_property = assertion.css_property
                assertion_op = assertion.assertion_type
                expected_value = assertion.value
                
                # 获取元素的实际样式值
                actual_value = page.locator(selector).evaluate(
                    """(element, prop) => {
                        return window.getComputedStyle(element).getPropertyValue(prop);
                    }""", 
                    css_property
                )
                
                # 比较样式值
                passed = self._compare_css_values(actual_value, expected_value, assertion_op)
                if not passed:
                    return False, f"元素 {selector} 的CSS属性 {css_property} 值为 '{actual_value}'，不满足 '{assertion_op} {expected_value}' 的条件"

            elif assertion_type == "assert_text_content":
                selector = assertion.selector
                locator = page.locator(selector)
                assertion_op = assertion.assertion_type
                expected_value = assertion.value
                
                try:
                    actual_text = locator.text_content(timeout=5000)
                    actual_text = actual_text.replace('\n', ' ').replace('\r', ' ').strip()
                except Exception:
                    return False, f"找不到或无法获取选择器 '{selector}' 的文本内容"
                
                if assertion_op == 'contains':
                    if expected_value not in actual_text:
                        return False, f"元素 '{selector}' 的文本 '{actual_text}' 不包含 '{expected_value}'"
                elif assertion_op == 'matches_regex':
                    import re
                    if not re.search(expected_value, actual_text):
                        return False, f"元素 '{selector}' 的文本 '{actual_text}' 不匹配正则表达式 '{expected_value}'"
                elif assertion_op == 'equals':
                    # 比较时去除前后空格，增强健壮性
                    if actual_text.strip().replace(' ', '') != expected_value.strip().replace(' ', ''):
                        return False, f"元素 '{selector}' 的文本为 '{actual_text}'，不等于期望的 '{expected_value}'"
                else:
                    return False, f"不支持的文本断言类型: '{assertion_op}'"

            elif assertion_type == "assert_attribute":
                selector = assertion.selector
                attribute = assertion.attribute
                assertion_op = assertion.assertion_type
                expected_value = assertion.value
                
                # 检查元素是否存在
                locator = page.locator(selector)
                count = locator.count()
                
                if count == 0:
                    return False, f"找不到匹配选择器 '{selector}' 的元素"
                
                # 如果只是检查属性是否存在
                if assertion_op == "exists":
                    # 检查元素是否有这个属性
                    has_attr = locator.evaluate(
                        """(element, attr) => {
                            return element.hasAttribute(attr);
                        }""", 
                        attribute
                    )
                    if not has_attr:
                        return False, f"元素 {selector} 没有属性 '{attribute}'"
                elif assertion_op == "not_exists":
                    # 检查元素是否没有这个属性
                    has_attr = locator.evaluate(
                        """(element, attr) => {
                            return element.hasAttribute(attr);
                        }""", 
                        attribute
                    )
                    if has_attr:
                        return False, f"元素 {selector} 不应该有属性 '{attribute}'，但实际存在"
                else:
                    # 获取属性值并比较
                    actual_value = locator.evaluate(
                        """(element, attr) => {
                            return element.getAttribute(attr);
                        }""", 
                        attribute
                    )
                    
                    # 如果元素没有这个属性
                    if actual_value is None:
                        return False, f"元素 {selector} 没有属性 '{attribute}'"
                    
                    # 比较属性值
                    if assertion_op == "equals":
                        if actual_value != expected_value:
                            return False, f"元素 {selector} 的属性 '{attribute}' 值为 '{actual_value}'，期望值为 '{expected_value}'"
                    elif assertion_op == "not_equals":
                        if actual_value == expected_value:
                            return False, f"元素 {selector} 的属性 '{attribute}' 值为 '{actual_value}'，不应该等于 '{expected_value}'"
                    elif assertion_op == "contains":
                        if expected_value not in actual_value:
                            return False, f"元素 {selector} 的属性 '{attribute}' 值为 '{actual_value}'，不包含期望值 '{expected_value}'"
                    elif assertion_op == "not_contains":
                        if expected_value in actual_value:
                            return False, f"元素 {selector} 的属性 '{attribute}' 值为 '{actual_value}'，不应该包含期望值 '{expected_value}'"
                    elif assertion_op == "starts_with":
                        if not actual_value.startswith(expected_value):
                            return False, f"元素 {selector} 的属性 '{attribute}' 值为 '{actual_value}'，不以期望值 '{expected_value}' 开头"
                    elif assertion_op == "ends_with":
                        if not actual_value.endswith(expected_value):
                            return False, f"元素 {selector} 的属性 '{attribute}' 值为 '{actual_value}'，不以期望值 '{expected_value}' 结尾"
                    elif assertion_op == "regex":
                        import re
                        try:
                            if not re.match(expected_value, actual_value):
                                return False, f"元素 {selector} 的属性 '{attribute}' 值为 '{actual_value}'，不匹配正则表达式 '{expected_value}'"
                        except re.error as e:
                            return False, f"正则表达式 '{expected_value}' 错误: {e}"

            elif assertion_type == "assert_element":
                selector = assertion.selector
                assertion_op = assertion.assertion_type
                expected_value = assertion.value
                
                # 检查元素是否存在
                locator = page.locator(selector)
                count = locator.count()
                
                if assertion_op == "exists":
                    if count == 0:
                        return False, f"找不到匹配选择器 '{selector}' 的元素"
                elif assertion_op == "not_exists":
                    if count > 0:
                        return False, f"不应该存在匹配选择器 '{selector}' 的元素，但找到了 {count} 个"
                else:
                    # 其他操作需要获取元素的文本内容进行比较
                    if count == 0:
                        return False, f"找不到匹配选择器 '{selector}' 的元素"
                    
                    try:
                        actual_text = locator.text_content(timeout=5000)
                    except Exception:
                        return False, f"无法获取选择器 '{selector}' 的文本内容"
                    
                    if assertion_op == "equals":
                        if actual_text != expected_value:
                            return False, f"元素 '{selector}' 的文本为 '{actual_text}'，不等于期望的 '{expected_value}'"
                    elif assertion_op == "contains":
                        if expected_value not in actual_text:
                            return False, f"元素 '{selector}' 的文本 '{actual_text}' 不包含 '{expected_value}'"
                    else:
                        return False, f"不支持的元素断言类型: '{assertion_op}'"

            elif assertion_type == "custom_script":
                script = assertion.script
                try:
                    if not (script.startswith("(()") and script.endswith(")()")):
                        # 用IIFE包装
                        script = f"(() => {{ {script} }})()"
                    # 执行自定义脚本
                    result = page.evaluate(script)
                    
                    # 如果脚本返回false或falsy值，则断言失败
                    if not result:
                        return False, f"自定义脚本返回结果为 {result}，断言失败"
                except Exception as e:
                    return False, f"执行自定义脚本时发生错误: {e}"

            else:
                return False, f"不支持的断言类型: '{assertion_type}'"

            return True, "通过"
        except AssertionError as e:
            return False, str(e)
        except Exception as e:
            return False, f"执行断言时发生错误: {e}"

    def _compare_css_values(self, actual_value: str, expected_value: str, assertion_op: str) -> bool:
        """
        比较CSS值的辅助方法
        
        Args:
            actual_value: 实际的CSS值
            expected_value: 期望的CSS值
            assertion_op: 比较操作符
            
        Returns:
            比较结果
        """
        # 清理值（去除首尾空格）
        actual_value = actual_value.strip().lower()
        expected_value = expected_value.strip().lower()
        
        # 处理font-weight特殊值映射
        font_weight_mapping = {
            'bold': '700',
            '700': 'bold',
            'normal': '400',
            '400': 'normal',
            # 它们的计算值取决于父元素的字重
        }
        
        # 如果是font-weight相关的比较，进行特殊处理
        if assertion_op == "equals":
            # 检查是否为font-weight值的等价比较
            if (actual_value in font_weight_mapping and 
                font_weight_mapping[actual_value] == expected_value) or \
               (expected_value in font_weight_mapping and 
                font_weight_mapping[expected_value] == actual_value):
                return True
        
        # 解析单位
        def parse_value_with_unit(value):
            import re
            match = re.match(r'^([+-]?(?:\d+\.?\d*|\.\d+))([a-zA-Z%]*)$', value)
            if match:
                num, unit = match.groups()
                return float(num), unit.lower()  # 单位也进行小写化
            return value, ""
        
        # 尝试进行颜色比较
        norm_actual = self._normalize_color_value(actual_value)
        norm_expected = self._normalize_color_value(expected_value)
        is_actual_color = norm_actual.startswith(('#', 'rgba'))
        is_expected_color = norm_expected.startswith(('#', 'rgba'))

        if is_actual_color and is_expected_color:
            if assertion_op == 'equals':
                return norm_actual == norm_expected
            elif assertion_op == 'not_equals':
                return norm_actual != norm_expected
        
        # 数值比较需要解析单位
        try:
            actual_num, actual_unit = parse_value_with_unit(actual_value)
            expected_num, expected_unit = parse_value_with_unit(expected_value)

            # 检查单位是否一致（如果不一致，需要转换）
            if actual_unit != expected_unit and actual_unit and expected_unit:
                # 简单的单位转换（支持常见的CSS单位转换）
                conversion_factors = {
                    # 长度单位相对于px的转换因子
                    'px': 1,
                    'pt': 4/3,
                    'pc': 16,
                    'in': 96,
                    'cm': 96/2.54,
                    'mm': 96/25.4,
                    # 百分比需要特殊处理
                    '%': None
                }

                # 如果单位可以转换
                if actual_unit in conversion_factors and expected_unit in conversion_factors:
                    if actual_unit != '%' and expected_unit != '%':
                        # 转换actual值到expected单位
                        actual_in_px = actual_num * conversion_factors[actual_unit]
                        actual_num = actual_in_px / conversion_factors[expected_unit]
                        actual_unit = expected_unit

            # 数值比较
            if assertion_op == "equals":
                return actual_num == expected_num
            if assertion_op == "greater_than":
                return actual_num > expected_num
            elif assertion_op == "less_than":
                return actual_num < expected_num
            elif assertion_op == "greater_than_or_equal":
                return actual_num >= expected_num
            elif assertion_op == "less_than_or_equal":
                return actual_num <= expected_num
            elif assertion_op == "contains":
                return str(expected_value) in str(actual_value)
            elif assertion_op == "exists":
                return actual_value != "" and actual_value != "none"
        except (ValueError, TypeError):
            # 如果解析失败，回退到字符串比较
            pass

        # 对于非数值比较，直接字符串比较（大小写不敏感）
        if assertion_op == "equals":
            return actual_value == expected_value
        elif assertion_op == "contains":
            return expected_value in actual_value
        elif assertion_op == "not_equals":
            return actual_value != expected_value
        elif assertion_op == "not_contain":
            return expected_value not in actual_value

        # 默认返回False
        return False
    @staticmethod
    def _normalize_color_value(color_value: str) -> str:
        """
        将颜色值标准化为统一格式，便于比较
        
        Args:
            color_value: 颜色值字符串
            
        Returns:
            标准化后的颜色值
        """
        # 移除空格和可能的rgba()或rgb()包装
        color_value = color_value.strip().lower()
        
        # 处理十六进制颜色值
        if color_value.startswith('#'):
            # 扩展3位十六进制颜色值到6位
            if len(color_value) == 4:  # #RGB格式
                color_value = '#' + color_value[1]*2 + color_value[2]*2 + color_value[3]*2
            return color_value
        
        # 处理rgb()格式
        if color_value.startswith('rgb('):
            # 提取rgb值
            import re
            match = re.search(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_value)
            if match:
                r, g, b = map(int, match.groups())
                return f"#{r:02x}{g:02x}{b:02x}"
        
        # 处理rgba()格式（忽略alpha通道）
        if color_value.startswith('rgba('):
            # 提取rgb值
            import re
            match = re.search(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[\d.]+\s*\)', color_value)
            if match:
                r, g, b = map(int, match.groups())
                return f"#{r:02x}{g:02x}{b:02x}"
        
        # 处理常见的颜色名称
        color_names = {
            'black': '#000000',
            'white': '#ffffff',
            'red': '#ff0000',
            'green': '#008000',
            'blue': '#0000ff',
            'yellow': '#ffff00',
            'orange': '#ffa500',
            'purple': '#800080',
            'gray': '#808080',
            'pink': '#ffc0cb',
            'brown': '#a52a2a',
            'cyan': '#00ffff',
            'magenta': '#ff00ff',
            'lime': '#00ff00',
            'maroon': '#800000',
            'navy': '#000080',
            'olive': '#808000',
            'silver': '#c0c0c0',
            'teal': '#008080',
            'transparent': 'rgba(0,0,0,0)'
        }
        
        if color_value in color_names:
            return color_names[color_value]
        
        # 其他情况直接返回原值
        return color_value


# 默认实例
sandbox_service = SandboxService()
