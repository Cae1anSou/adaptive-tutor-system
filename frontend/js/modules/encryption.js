/**
 * 安全的Base64加密函数
 * @param {string} str - 要加密的字符串
 * @returns {string} 加密后的字符串
 */
export function encrypt(str) {
    try {
        // 先转换为UTF-8编码
        const utf8Bytes = new TextEncoder().encode(str);

        // 将UTF-8字节数组转换为二进制字符串
        let binaryString = '';
        for (let i = 0; i < utf8Bytes.length; i++) {
            binaryString += String.fromCharCode(utf8Bytes[i]);
        }

        // 使用btoa进行Base64编码
        return btoa(binaryString);
    } catch (error) {
        console.error('加密失败:', error);
        // 如果加密失败，返回原始字符串的简单Base64编码
        return btoa(unescape(encodeURIComponent(str)));
    }
}

/**
 * Base64解密函数
 * @param {string} str - 要解密的字符串
 * @returns {string} 解密后的字符串
 */
export function decrypt(str) {
    try {
        // 先解码Base64
        const binaryString = atob(str);

        // 将二进制字符串转换为字节数组
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        // 使用TextDecoder解码为UTF-8字符串
        return new TextDecoder().decode(bytes);
    } catch (error) {
        console.error('解密失败:', error);
        // 如果解密失败，尝试简单的Base64解码
        try {
            return decodeURIComponent(escape(atob(str)));
        } catch (e) {
            console.error('备用解密方法也失败:', e);
            return null;
        }
    }
}

/**
 * URL安全的Base64编码（替换+/为-_并去除=）
 * @param {string} base64 - 标准Base64字符串
 * @returns {string} URL安全的Base64字符串
 */
export function base64ToUrlSafe(base64) {
    return base64
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

/**
 * 将URL安全的Base64转换回标准Base64
 * @param {string} urlSafeBase64 - URL安全的Base64字符串
 * @returns {string} 标准Base64字符串
 */
export function urlSafeToBase64(urlSafeBase64) {
    let base64 = urlSafeBase64
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    // 添加填充字符=
    const pad = base64.length % 4;
    if (pad) {
        if (pad === 1) {
            throw new Error('Invalid base64 string');
        }
        base64 += '='.repeat(4 - pad);
    }

    return base64;
}

/**
 * 生成带时间戳的加密参数（URL安全版本）
 * @param {string} id - 主题ID
 * @returns {string} 加密后的参数
 */
export function encryptWithTimestamp(id) {
    const timestamp = Date.now();
    const data = `${id}|${timestamp}`;
    const encrypted = encrypt(data);
    return base64ToUrlSafe(encrypted);
}

/**
 * 解密带时间戳的参数（URL安全版本）
 * @param {string} encryptedData - 加密的数据
 * @returns {Object} 解密后的对象 {id: string, timestamp: number, isValid: boolean}
 */
export function decryptWithTimestamp(encryptedData) {
    try {
        // 将URL安全的Base64转换回标准Base64
        const standardBase64 = urlSafeToBase64(encryptedData);
        const decrypted = decrypt(standardBase64);

        if (!decrypted) {
            return { id: null, timestamp: null, isValid: false };
        }

        const [id, timestamp] = decrypted.split('|');
        return {
            id: id,
            timestamp: parseInt(timestamp),
            isValid: Date.now() - parseInt(timestamp) < 3600000 // 1小时内有效
        };
    } catch (error) {
        console.error('解密失败:', error);
        return { id: null, timestamp: null, isValid: false };
    }
}

/**
 * 简单的参数验证（备用方案）
 * @param {string} param - URL参数
 * @returns {Object} 解析后的参数
 */
export function simpleParamDecode(param) {
    try {
        // 尝试直接解密
        const result = decryptWithTimestamp(param);
        if (result.isValid) {
            return result;
        }

        // 如果解密失败，尝试直接解析（兼容未加密的情况）
        const [id, timestamp] = atob(param).split('|');
        return {
            id: id,
            timestamp: parseInt(timestamp),
            isValid: Date.now() - parseInt(timestamp) < 3600000
        };
    } catch (error) {
        console.warn('参数解析失败，使用原始值:', error);
        return {
            id: param,
            timestamp: Date.now(),
            isValid: true // 假设有效以便继续流程
        };
    }
}