
// ==================== 常量定义 ====================
const MAX_Z_INDEX = 2147483646;

const MESSAGE_TYPES = {
    START: 'SW_SELECT_START',
    STOP: 'SW_SELECT_STOP',
    CHOSEN: 'SW_SELECT_CHOSEN',
    UPDATE_MODE: 'SW_UPDATE_CUMULATIVE_MODE'
};

// ==================== 工具函数 ====================
function getElementAtPoint(x, y) {
    const elementsStack = document.elementsFromPoint(x, y);
    const refElement = elementsStack.find((element) => !element.closest('svg') &&
        !element.closest('.sw-selector') &&
        isElementAtPoint(element, x, y)) || document.body;
    return refElement;
}

function isElementAtPoint(element, clientX, clientY) {
    const boundingRect = element.getBoundingClientRect();
    const isInHorizontalBounds = clientX >= boundingRect.left &&
        clientX <= boundingRect.left + boundingRect.width;
    const isInVerticalBounds = clientY >= boundingRect.top &&
        clientY <= boundingRect.top + boundingRect.height;
    return isInHorizontalBounds && isInVerticalBounds;
}

function getElementXPath(element) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) {
        return '';
    }
    if (element.id) {
        return `//*[@id="${element.id}"]`;
    }
    
    const paths = [];
    for (; element && element.nodeType === Node.ELEMENT_NODE; element = element.parentNode) {
        let index = 0;
        let hasFollowingSiblings = false;
        
        for (let sibling = element.previousSibling; sibling; sibling = sibling.previousSibling) {
            if (sibling.nodeType !== Node.ELEMENT_NODE) continue;
            if (sibling.tagName === element.tagName) {
                index++;
            }
        }
        
        for (let sibling = element.nextSibling; sibling && !hasFollowingSiblings; sibling = sibling.nextSibling) {
            if (sibling.nodeType !== Node.ELEMENT_NODE) continue;
            if (sibling.tagName === element.tagName) {
                hasFollowingSiblings = true;
            }
        }
        
        const tagName = element.tagName.toLowerCase();
        const pathIndex = (index || hasFollowingSiblings) ? `[${index + 1}]` : '';
        paths.unshift(tagName + pathIndex);
        
        if (element.id) {
            paths.unshift(`*[@id="${element.id}"]`);
            break;
        }
    }
    return '/' + paths.join('/');
}

function getElementInfo(element) {
    const bbox = element.getBoundingClientRect();
    const computedStyle = window.getComputedStyle(element);
    
    return {
        tagName: element.tagName.toLowerCase(),
        id: element.id || '',
        className: element.className || '',
        classList: Array.from(element.classList || []),
        textContent: element.textContent?.trim().substring(0, 100) || '',
        outerHTML: element.outerHTML || '',
        selector: getElementXPath(element),
        bounds: { x: bbox.left, y: bbox.top, width: bbox.width, height: bbox.height },
        styles: {
            backgroundColor: computedStyle.backgroundColor,
            color: computedStyle.color,
            fontSize: computedStyle.fontSize
        },
        pageURL: window.location.href
    };
}

// ==================== 核心选择器类 ====================
class ElementSelector {
    constructor(options = {}) {
        this.selectorEl = null;
        this.highlightEl = null;
        this.lastHoveredElement = null;
        this.isActive = false;
        this.currentElements = options.currentElements || [];
        this.cumulativeElements = options.cumulativeElements || [];
        
        this.options = {
            ignoreSelectors: ['.sw-selector', '.sw-highlight'],
            allowedTags: [],
            ...options
        };
        
        console.log('[ElementSelector] 构造函数初始化，allowedElements:', this.options.allowedElements);
        console.log('[ElementSelector] currentElements:', this.currentElements);
        console.log('[ElementSelector] cumulativeElements:', this.cumulativeElements);
        
        // 绑定事件处理器
        this.handleMouseMove = this.handleMouseMove.bind(this);
        this.handleMouseLeave = this.handleMouseLeave.bind(this);
        this.handleMouseClick = this.handleMouseClick.bind(this);
        this.handleKeyDown = this.handleKeyDown.bind(this);
    }
    
    // ==================== 生命周期方法 ====================
    start() {
        if (this.isActive) return;
        console.log('[ElementSelector] 启动选择器...');
        this.isActive = true;
        this.createSelectorElement();
        this.createHighlightElement();
        this.bindEscapeKey();
        
        // 给body添加选择器激活类
        document.body.classList.add('sw-selector-active');
        document.documentElement.classList.add('sw-selector-active');
        
        console.log('[ElementSelector] 选择器启动完成，isActive:', this.isActive);
    }
    
    stop() {
        if (!this.isActive) return;
        console.log('[ElementSelector] 停止选择器...');
        this.isActive = false;
        this.removeSelectorElement();
        this.removeHighlightElement();
        this.unbindEscapeKey();
        
        // 移除选择器激活类
        document.body.classList.remove('sw-selector-active');
        document.documentElement.classList.remove('sw-selector-active');
        
        if (this.options.onClose) {
            this.options.onClose();
        }
        console.log('[ElementSelector] 选择器已停止');
    }
    
    // ==================== 累积模式更新 ====================
    updateCumulativeMode(isCumulative, allowedElements) {
        console.log('[ElementSelector] 更新累积模式:', isCumulative, '（true=累积模式，false=当前章节模式）');
        
        // 更新允许的元素列表
        if (typeof allowedElements === 'object' && !Array.isArray(allowedElements)) {
            this.currentElements = allowedElements.current || [];
            this.cumulativeElements = allowedElements.cumulative || [];
            console.log('[ElementSelector] 当前章节元素数量:', this.currentElements.length, '，累积元素数量:', this.cumulativeElements.length);
        }
        
        // 根据累积模式设置实际使用的元素列表
        if (isCumulative) {
            this.options.allowedElements = this.cumulativeElements;
            console.log('[ElementSelector] 启用累积模式，可选元素数量:', this.cumulativeElements.length);
        } else {
            this.options.allowedElements = this.currentElements;
            console.log('[ElementSelector] 启用当前章节模式，可选元素数量:', this.currentElements.length);
        }
        
        console.log('[ElementSelector] 当前允许的元素:', this.options.allowedElements);
        
        // 如果当前有高亮元素，重新检查是否仍然可选
        if (this.lastHoveredElement) {
            if (this.shouldIgnoreElement(this.lastHoveredElement)) {
                this.hideHighlight();
                this.lastHoveredElement = null;
                console.log('[ElementSelector] 当前高亮元素不再可选，已隐藏高亮');
            } else {
                // 重新更新高亮显示以反映新的颜色
                this.updateHighlight(this.lastHoveredElement);
                console.log('[ElementSelector] 更新当前高亮元素的显示');
            }
        }
    }
    
    // ==================== 事件处理方法 ====================
    handleMouseMove(event) {
        requestAnimationFrame(() => {
            if (this.highlightEl && this.highlightEl.style.display !== 'none') {
                this.highlightEl.style.display = 'none';
            }
            
            const refElement = getElementAtPoint(event.clientX, event.clientY);
            if (!refElement) {
                this.hideHighlight();
                return;
            }
            
            // 首先检查元素是否应该忽略
            if (this.shouldIgnoreElement(refElement)) {
                this.hideHighlight();
                return;
            }
            
            // 手动检查元素是否在允许列表中
            const tagName = refElement.tagName.toLowerCase();
            if (!this.options.allowedElements.includes(tagName)) {
                this.hideHighlight();
                return;
            }
            
            if (this.lastHoveredElement === refElement) {
                if (this.highlightEl && this.highlightEl.style.display === 'none') {
                    this.updateHighlight(refElement);
                }
                return;
            }
            
            if (this.lastHoveredElement !== refElement) {
                if (this.lastHoveredElement && this.options.onElementUnhovered) {
                    this.options.onElementUnhovered();
                }
                this.lastHoveredElement = refElement;
                this.updateHighlight(refElement);
                if (this.options.onElementHovered) {
                    this.options.onElementHovered(refElement);
                }
            }
        });
    }
    
    handleMouseLeave() {
        this.hideHighlight();
        this.lastHoveredElement = null;
        if (this.options.onElementUnhovered) {
            this.options.onElementUnhovered();
        }
    }
    
    handleMouseClick(event) {
        event.preventDefault();
        event.stopPropagation();
        if (!this.lastHoveredElement) return;
        if (this.shouldIgnoreElement(this.lastHoveredElement)) return;
        
        const elementInfo = getElementInfo(this.lastHoveredElement);
        if (this.options.onElementSelected) {
            this.options.onElementSelected(this.lastHoveredElement, elementInfo);
        }
        this.stop();
    }
    
    handleKeyDown(event) {
        if (event.key === 'Escape') {
            this.stop();
        }
    }
    
    // ==================== 元素过滤方法 ====================
    shouldIgnoreElement(element) {
        if (!element) return true;
        
        const tag = element.tagName.toLowerCase();
        
        // 检查是否在允许的元素列表中
        if (this.options.allowedElements && this.options.allowedElements.length > 0) {
            // 如果是字符串数组，直接检查是否包含当前标签
            if (Array.isArray(this.options.allowedElements)) {
                const isAllowed = this.options.allowedElements.includes(tag);
                if (!isAllowed) {
                    return true; // 如果不在允许列表中，应该忽略
                }
            } else {
                const isAllowed = this.options.allowedElements.some(allowed => {
                    if (typeof allowed === 'string') {
                        return tag === allowed.toLowerCase();
                    }
                    if (allowed.tagName) {
                        return tag === allowed.tagName.toLowerCase();
                    }
                    return false;
                });
                
                if (!isAllowed) {
                    return true; // 如果不在允许列表中，应该忽略
                }
            }
        }
        
        // 检查允许的标签
        if (this.options.allowedTags && this.options.allowedTags.length > 0) {
            if (!this.options.allowedTags.includes(tag)) {
                return true;
            }
        }
        
        // 检查忽略的选择器
        const ignoreSelectors = this.options.ignoreSelectors || [];
        return ignoreSelectors.some(selector => {
            if (selector.startsWith('.')) {
                return element.classList.contains(selector.substring(1));
            }
            if (selector.startsWith('#')) {
                return element.id === selector.substring(1);
            }
            return element.matches(selector);
        });
    }
    
    // ==================== DOM元素管理 ====================
    createSelectorElement() {
        if (this.selectorEl) return;
        
        const selectorEl = document.createElement('div');
        selectorEl.className = 'sw-selector';
        
        // 直接设置样式，不使用动态CSS
        Object.assign(selectorEl.style, {
            position: 'fixed',
            inset: '0',
            width: '100vw',
            height: '100vh',
            backgroundColor: 'rgba(0, 0, 0, 0.01)',
            zIndex: String(MAX_Z_INDEX),
            cursor: 'crosshair',
            pointerEvents: 'auto'
        });
        
        selectorEl.addEventListener('mousemove', this.handleMouseMove);
        selectorEl.addEventListener('mouseleave', this.handleMouseLeave);
        selectorEl.addEventListener('click', this.handleMouseClick);
        document.body.appendChild(selectorEl);
        this.selectorEl = selectorEl;
        
        console.log('[ElementSelector] 选择器元素已创建并添加到DOM');
    }
    
    createHighlightElement() {
        if (this.highlightEl) return;
        
        const highlightEl = document.createElement('div');
        highlightEl.className = 'sw-highlight';
        Object.assign(highlightEl.style, {
            position: 'fixed',
            display: 'none',
            pointerEvents: 'none',
            border: '2px solid #0079d3',
            backgroundColor: 'rgba(0, 121, 211, 0.1)',
            zIndex: String(MAX_Z_INDEX - 1)
        });
        document.body.appendChild(highlightEl);
        this.highlightEl = highlightEl;
    }
    
    removeSelectorElement() {
        if (!this.selectorEl) return;
        
        this.selectorEl.removeEventListener('mousemove', this.handleMouseMove);
        this.selectorEl.removeEventListener('mouseleave', this.handleMouseLeave);
        this.selectorEl.removeEventListener('click', this.handleMouseClick);
        document.body.removeChild(this.selectorEl);
        this.selectorEl = null;
    }
    
    removeHighlightElement() {
        if (!this.highlightEl) return;
        
        document.body.removeChild(this.highlightEl);
        this.highlightEl = null;
        this.lastHoveredElement = null;
    }
    
    // ==================== 键盘事件管理 ====================
    bindEscapeKey() {
        document.addEventListener('keydown', this.handleKeyDown);
    }
    
    unbindEscapeKey() {
        document.removeEventListener('keydown', this.handleKeyDown);
    }
    
    // ==================== 高亮显示管理 ====================
    updateHighlight(element) {
        if (!this.highlightEl || !element) return;
        
        const rect = element.getBoundingClientRect();
        const tagName = element.tagName.toLowerCase();
        
        // 判断元素类型并设置相应的颜色
        let borderColor, backgroundColor;
        
        // 首先检查元素是否在当前允许的元素列表中
        const isAllowed = this.options.allowedElements && this.options.allowedElements.includes(tagName);
        
        if (!isAllowed) {
            // 如果不在允许列表中，则不显示高亮
            this.hideHighlight();
            return;
        }
        
        // 检查是否是当前章节的元素
        const isCurrentElement = this.currentElements.includes(tagName);
        // 检查是否是之前章节的元素
        const isPreviousElement = this.cumulativeElements.includes(tagName) && !isCurrentElement;
        
        if (isCurrentElement) {
            // 当前章节元素 - 蓝色
            borderColor = '#0079d3';
            backgroundColor = 'rgba(0, 121, 211, 0.1)';
        } else if (isPreviousElement) {
            // 之前章节元素 - 红色
            borderColor = '#dc3545';
            backgroundColor = 'rgba(220, 53, 69, 0.1)';
        }
        
        Object.assign(this.highlightEl.style, {
            display: 'block',
            left: `${rect.left}px`,
            top: `${rect.top}px`,
            width: `${rect.width}px`,
            height: `${rect.height}px`,
            border: `2px solid ${borderColor}`,
            backgroundColor: backgroundColor
        });
    }
    
    hideHighlight() {
        if (!this.highlightEl) return;
        this.highlightEl.style.display = 'none';
    }
}

// ==================== iframe通信桥接 ====================
function initIframeSelector(options = {}) {
    const { allowed = true, allowedOrigins = ['*'], allowedTags = [] } = options;
    if (!allowed) return () => {};
    
    let selector = null;
    const handleMessage = (event) => {
        if (allowedOrigins[0] !== '*' && !allowedOrigins.includes(event.origin)) return;
        
        let message;
        try {
            message = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
        } catch (e) { return; }
        
        switch (message.type) {
            case MESSAGE_TYPES.START:
                console.log('[initIframeSelector] 接收到START消息');
                console.log('[initIframeSelector] 检查 isCumulative 字段:', message.hasOwnProperty('isCumulative') ? message.isCumulative : '未定义');
                
                if (selector) {
                    selector.stop();
                }
                const startMessage = message;
                const allowedElements = startMessage.allowedElements || [];
                let currentElements = [];
                let cumulativeElements = [];
                
                if (typeof allowedElements === 'object' && !Array.isArray(allowedElements)) {
                    currentElements = allowedElements.current || [];
                    cumulativeElements = allowedElements.cumulative || [];
                } else {
                    cumulativeElements = allowedElements;
                }
                
                console.log('[initIframeSelector] 元素解析: 当前(', currentElements.length, ')，累积(', cumulativeElements.length, ')');
                
                // 创建ElementSelector实例
                // 根据传递的消息决定初始允许的元素
                let initialAllowedElements = cumulativeElements;
                
                // 检查启动消息中是否包含累积模式标志
                if (startMessage.hasOwnProperty('isCumulative')) {
                    if (startMessage.isCumulative) {
                        initialAllowedElements = cumulativeElements;
                        console.log('[initIframeSelector] 使用累积模式 - 可选择所有累积到当前章节的元素, 元素数量:', cumulativeElements.length);
                    } else {
                        initialAllowedElements = currentElements;
                        console.log('[initIframeSelector] 使用当前章节模式 - 只能选择当前章节的元素, 元素数量:', currentElements.length);
                    }
                } else {
                    console.log('[initIframeSelector] 未指定模式，默认使用当前章节模式');
                    initialAllowedElements = currentElements;
                }
                
                selector = new ElementSelector({
                    ignoreSelectors: startMessage.ignore,
                    allowedTags: startMessage.allowedTags || allowedTags,
                    allowedElements: initialAllowedElements,
                    currentElements: currentElements,
                    cumulativeElements: cumulativeElements,
                    onElementSelected: (element, info) => {
                        try {
                            if (window.parent && window.parent.postMessage) {
                                window.parent.postMessage({
                                    type: MESSAGE_TYPES.CHOSEN,
                                    payload: info
                                }, '*');
                            } else {
                                console.warn('无法发送postMessage到父窗口');
                            }
                        } catch (error) {
                            console.error('发送postMessage失败:', error);
                        }
                    }
                });
                console.log('[initIframeSelector] 创建选择器，设置允许元素:', initialAllowedElements);
                selector.start();
                console.log('[initIframeSelector] 选择器启动，初始允许元素数量:', initialAllowedElements.length);
                
                // 添加明确的日志信息，说明当前使用的模式
                const actuallyUsingCumulative = initialAllowedElements === cumulativeElements;
                if (actuallyUsingCumulative) {
                    console.log('[initIframeSelector] 使用累积模式');
                } else {
                    console.log('[initIframeSelector] 使用当前章节模式');
                }
                break;
            case MESSAGE_TYPES.STOP:
                if (selector) {
                    selector.stop();
                    selector = null;
                }
                console.log('[initIframeSelector] 选择器停止');
                break;
            case MESSAGE_TYPES.UPDATE_MODE:
                if (selector) {
                    const updateMessage = message;
                    console.log('[initIframeSelector] 接收到累积模式更新消息:', updateMessage);
                    selector.updateCumulativeMode(updateMessage.isCumulative, updateMessage.allowedElements);
                } else {
                    console.warn('[initIframeSelector] 选择器未初始化，无法更新累积模式');
                }
                break;
        }
    };
    
    window.addEventListener('message', handleMessage);
    return () => {
        window.removeEventListener('message', handleMessage);
        if (selector) {
            selector.stop();
            selector = null;
        }
    };
}

function createSelectorBridge(options) {
    const { iframeWindow, targetOrigin = '*', ignoreSelectors = ['.sw-selector', '.sw-highlight'], onChosen, onError } = options;
    
    if (!iframeWindow) throw new Error('Invalid iframe window');
    
    const handleMessage = (event) => {
        let message;
        try {
            message = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
        } catch (e) { return; }
        
        if (message.type === MESSAGE_TYPES.CHOSEN && onChosen) {
            const chosenMessage = message;
            onChosen(chosenMessage.payload);
        }
    };
    
    window.addEventListener('message', handleMessage);
    
    return {
        start(allowedTags = [], allowedElements = []) {
            try {
                if (!iframeWindow || !iframeWindow.postMessage) {
                    console.warn('iframe window未准备就绪，无法发送消息');
                    if (onError) {
                        onError(new Error('iframe window未准备就绪'));
                    }
                    return;
                }
                
                let elementsToSend = allowedElements;
                
                if (typeof allowedElements === 'object' && !Array.isArray(allowedElements)) {
                    elementsToSend = allowedElements;
                } else {
                    elementsToSend = {
                        current: allowedElements,
                        cumulative: allowedElements
                    };
                }
                
                // 获取当前的累积模式状态
                // 注意：这里的逻辑是当开关被选中时，启用累积模式（可选择所有章节元素）
                // 当开关未选中时，仅使用当前章节元素
                let isCumulative = false;
                try {
                    const toggle = document.getElementById('cumulativeToggle');
                    if (toggle) {
                        isCumulative = toggle.checked;
                        console.log('[选择器桥接] 获取开关状态:', isCumulative, '（选中=累积模式，未选中=当前章节模式）');
                    }
                } catch (error) {
                    console.warn('无法获取开关状态:', error);
                }
                
                const message = {
                    type: MESSAGE_TYPES.START,
                    ignore: ignoreSelectors,
                    allowedTags,
                    allowedElements: elementsToSend,
                    isCumulative: isCumulative  // 传递累积模式状态
                };
                
                try {
                    iframeWindow.postMessage(message, targetOrigin);
                } catch (postMessageError) {
                    console.warn('postMessage发送失败:', postMessageError);
                    if (onError) {
                        onError(postMessageError instanceof Error ? postMessageError : new Error(String(postMessageError)));
                    }
                }
            } catch (error) {
                console.error('启动选择器失败:', error);
                if (onError) {
                    onError(error instanceof Error ? error : new Error(String(error)));
                }
            }
        },
        
        stop() {
            try {
                if (!iframeWindow || !iframeWindow.postMessage) {
                    console.warn('iframe window未准备就绪，无法发送停止消息');
                    return;
                }
                
                const message = {
                    type: MESSAGE_TYPES.STOP
                };
                
                try {
                    iframeWindow.postMessage(message, targetOrigin);
                } catch (postMessageError) {
                    console.warn('postMessage停止消息发送失败:', postMessageError);
                }
            } catch (error) {
                console.error('停止选择器失败:', error);
                if (onError) {
                    onError(error instanceof Error ? error : new Error(String(error)));
                }
            }
        },
        
        updateMode(isCumulative, allowedElements) {
            try {
                if (!iframeWindow || !iframeWindow.postMessage) {
                    console.warn('iframe window未准备就绪，无法发送模式更新消息');
                    return;
                }
                
                const message = {
                    type: MESSAGE_TYPES.UPDATE_MODE,
                    isCumulative: isCumulative,
                    allowedElements: allowedElements
                };
                
                try {
                    iframeWindow.postMessage(message, targetOrigin);
                } catch (postMessageError) {
                    console.warn('postMessage模式更新消息发送失败:', postMessageError);
                    if (onError) {
                        onError(postMessageError instanceof Error ? postMessageError : new Error(String(postMessageError)));
                    }
                }
            } catch (error) {
                console.error('更新模式失败:', error);
                if (onError) {
                    onError(error instanceof Error ? error : new Error(String(error)));
                }
            }
        },
        
        destroy() {
            window.removeEventListener('message', handleMessage);
        }
    };
}

// ==================== 公共API函数 ====================
function handleStartSelector(allowedElements, bridge, showStatus) {
    if (!bridge) {
        console.error('选择器桥接未初始化');
        return;
    }
    
    try {
        bridge.start([], allowedElements);
        // 不再显示选择器启动状态信息
        // showStatus('success', '选择器已启动，请点击要选择的元素');
    } catch (error) {
        console.error('启动选择器失败:', error);
    }
}

function stopSelector(bridge) {
    if (bridge) {
        bridge.stop();
        console.log('选择器已停止');
    }
}

function initBridge(createSelectorBridge, onElementSelected, onError) {
    const iframe = document.getElementById('element-selector-iframe');
    if (!iframe || !iframe.contentWindow) {
        console.error('iframe元素未找到或未加载');
        return null;
    }
    
    try {
        const bridge = createSelectorBridge({
            iframeWindow: iframe.contentWindow,
            onChosen: onElementSelected,
            onError: onError
        });
        
        console.log('选择器桥接初始化成功');
        return bridge;
    } catch (error) {
        console.error('初始化选择器桥接失败:', error);
        if (onError) {
            onError(error);
        }
        return null;
    }
}

function handleCumulativeToggle(allowedElements, showStatus, bridge) {
    const cumulativeToggle = document.getElementById('cumulativeToggle');
    if (cumulativeToggle) {
        const isCumulative = cumulativeToggle.checked;
        console.log('累积模式切换:', isCumulative, '（选中=累积模式，未选中=当前章节模式）');
        
        if (isCumulative) {
            console.log('当前模式: 累积模式 - 可选择所有累积到当前章节的元素。元素数量:', allowedElements.cumulative.length);
        } else {
            console.log('当前模式: 当前章节模式 - 只能选择当前章节的元素。元素数量:', allowedElements.current.length);
        }
        
        // 优先使用bridge的updateMode方法
        if (bridge && bridge.updateMode) {
            console.log('通过bridge发送模式更新消息...');
            bridge.updateMode(isCumulative, allowedElements);
        } else {
            // 备用方案：直接向iframe发送消息
            console.log('未找到bridge，尝试直接发送消息...');
            const iframe = document.getElementById('element-selector-iframe');
            if (iframe && iframe.contentWindow) {
                try {
                    const message = {
                        type: MESSAGE_TYPES.UPDATE_MODE,
                        isCumulative: isCumulative,
                        allowedElements: allowedElements
                    };
                    iframe.contentWindow.postMessage(message, '*');
                    console.log('消息发送成功，等待iframe响应...');
                } catch (error) {
                    console.warn('发送累积模式更新消息失败:', error);
                }
            }
        }
    } else {
        console.warn('[handleCumulativeToggle] 未找到cumulativeToggle元素');
    }
}

function handleShowSource() {
    const iframe = document.getElementById('element-selector-iframe');
    if (iframe && iframe.contentDocument) {
        const sourceCode = iframe.contentDocument.documentElement.outerHTML;
        console.log('页面源代码:', sourceCode);
        alert('源代码已输出到控制台，请按F12查看');
    } else {
        console.warn('无法获取iframe内容');
    }
}

function handleError(error, showStatus, onStop) {
    console.error('选择器错误:', error);
    
    if (onStop) {
        onStop();
    }
}

// ==================== 模块导出 ====================
export {
    getElementAtPoint,
    isElementAtPoint,
    getElementXPath,
    getElementInfo,
    ElementSelector,
    initIframeSelector,
    createSelectorBridge,
    handleStartSelector,
    stopSelector,
    initBridge,
    handleCumulativeToggle,
    handleShowSource,
    handleError,
    MESSAGE_TYPES
};

// ==================== 向后兼容性 ====================
window.SelectModules = {
    getElementAtPoint,
    isElementAtPoint,
    getElementXPath,
    getElementInfo,
    ElementSelector,
    initIframeSelector,
    createSelectorBridge,
    handleStartSelector,
    stopSelector,
    initBridge,
    handleCumulativeToggle,
    handleShowSource,
    handleError,
    MESSAGE_TYPES
};

// ==================== 自动初始化 ====================
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initIframeSelector();
    });
} else {
    initIframeSelector();
}