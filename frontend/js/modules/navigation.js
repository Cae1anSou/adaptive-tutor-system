import { encryptWithTimestamp, decryptWithTimestamp, simpleParamDecode } from './encryption.js';

// 存储最后一个来源页面
let lastReferrer = null;

/**
 * 记录来源页面（在页面加载时调用）
 */
export function trackReferrer() {
    // 记录当前页面作为下一个页面的来源
    lastReferrer = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    console.log('记录来源页面:', lastReferrer);
}
/**
 * 安全的页面跳转
 * @param {string} url - 目标URL
 * @param {string} id - 要传递的参数
 * @param {boolean} encryptData - 是否加密参数
 * @param {boolean} addReturn - 是否添加返回参数（仅测试页面使用）
 */
export function navigateTo(url, id = null, encryptData = true, addReturn = false) {
    let targetUrl = url;

    if (id) {
        let paramValue;
        if (encryptData) {
            paramValue = encryptWithTimestamp(id);
        } else {
            paramValue = id;
        }
        targetUrl += `?topic=${encodeURIComponent(paramValue)}`;

        // 只有在测试页面且明确要求时才添加返回参数
        if (addReturn && url.includes('test_page.html')) {
            const returnUrl = lastReferrer || '/pages/knowledge_graph.html';
            targetUrl += `&return=${encodeURIComponent(returnUrl)}`;
            console.log('添加返回参数:', returnUrl);
        }
    }

    console.log('跳转到:', targetUrl);
    window.location.href = targetUrl;
}

/**
 * 获取URL参数
 * @param {string} name - 参数名
 * @param {boolean} decryptData - 是否尝试解密参数
 * @returns {Object|string} 参数值
 */
export function getUrlParam(name, decryptData = true) {
    const urlParams = new URLSearchParams(window.location.search);
    const param = urlParams.get(name);

    if (!param) return null;

    if (decryptData) {
        try {
            // 先解码URL编码
            const decodedParam = decodeURIComponent(param);

            // 尝试解密
            const result = decryptWithTimestamp(decodedParam);

            if (result.isValid) {
                return result;
            } else {
                // 如果解密失败或过期，尝试备用解析方法
                console.warn('解密失败或参数过期，尝试备用解析');
                return simpleParamDecode(decodedParam);
            }
        } catch (error) {
            console.warn('参数解密失败，使用备用解析:', error);
            return simpleParamDecode(param);
        }
    }

    // 不解密时直接返回
    return param;
}

/**
 * 获取返回URL（仅测试页面使用）
 */
export function getReturnUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    const returnUrl = urlParams.get('return');

    if (returnUrl) {
        return decodeURIComponent(returnUrl);
    }

    // 默认返回知识图谱
    return '/pages/knowledge_graph.html';
}

/**
 * 返回上一页
 */
export function goBack() {
    const returnUrl = getReturnUrl();

    // 如果当前是测试页面且有返回URL，使用快速返回
    if (window.location.pathname.includes('test_page.html') && returnUrl) {
        console.log('快速返回到:', returnUrl);
        window.location.href = returnUrl;
    }
    // 如果是学习页面，返回首页（对照组没有知识图谱）
    else if (window.location.pathname.includes('learning_page.html')) {
        console.log('返回首页');
        window.location.href = '/index.html';
    }
    // 其他情况使用浏览器历史
    else if (window.history.length > 1) {
        window.history.back();
    } else {
        // 如果没有历史记录，跳转到首页
        window.location.href = '/index.html';
    }
}

/**
 * 设置标题点击事件
 * @param {string} targetUrl - 点击标题后跳转的URL
 */
export function setupHeaderTitle(targetUrl) {
    const headerTitle = document.getElementById('headerTitle');
    if (headerTitle) {
        headerTitle.style.cursor = 'pointer';
        headerTitle.addEventListener('click', () => {
            navigateTo(targetUrl);
        });
    }
}

/**
 * 设置返回按钮
 */
export function setupBackButton() {
    const backButton = document.getElementById('backButton');
    if (backButton) {
        backButton.addEventListener('click', goBack);
    }
}

/**
 * 调试函数：显示当前URL参数信息
 */
export function debugUrlParams() {
    const params = new URLSearchParams(window.location.search);
    console.log('URL参数:', Object.fromEntries(params.entries()));

    if (window.location.pathname.includes('test_page.html')) {
        console.log('返回URL:', getReturnUrl());
    }
}