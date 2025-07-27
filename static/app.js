/**
 * Base64 Web Client Application
 * 
 * 这个JavaScript应用程序为Base64编码解码工具提供前端交互功能。
 * 它通过HTTP API与后端服务通信，提供实时编码解码、文件处理和用户友好的界面。
 */

class Base64WebClient {
    constructor(apiBaseUrl = '') {
        this.apiBaseUrl = apiBaseUrl;
        this.initializeElements();
        this.initEventListeners();
        this.setupDragAndDrop();
    }
    
    /**
     * 初始化DOM元素引用
     */
    initializeElements() {
        // 编码相关元素
        this.textInput = document.getElementById('text-input');
        this.encodedOutput = document.getElementById('encoded-output');
        this.encodeBtn = document.getElementById('encode-btn');
        this.clearTextBtn = document.getElementById('clear-text-btn');
        this.copyEncodedBtn = document.getElementById('copy-encoded');
        this.textCharCount = document.getElementById('text-char-count');
        
        // 解码相关元素
        this.base64Input = document.getElementById('base64-input');
        this.decodedOutput = document.getElementById('decoded-output');
        this.decodeBtn = document.getElementById('decode-btn');
        this.clearBase64Btn = document.getElementById('clear-base64-btn');
        this.copyDecodedBtn = document.getElementById('copy-decoded');
        this.base64CharCount = document.getElementById('base64-char-count');
        
        // 文件处理相关元素
        this.fileInput = document.getElementById('file-input');
        this.fileOutput = document.getElementById('file-output');
        this.encodeFileBtn = document.getElementById('encode-file');
        this.copyFileResultBtn = document.getElementById('copy-file-result');
        this.downloadResultBtn = document.getElementById('download-result');
        this.fileProgress = document.getElementById('file-progress');
        this.progressFill = document.getElementById('progress-fill');
        this.progressText = document.getElementById('progress-text');
        this.dragDropArea = document.getElementById('drag-drop-area');
        this.selectedFileName = document.getElementById('selected-file-name');
        
        // 通知元素
        this.notification = document.getElementById('notification');
    }
    
    /**
     * 初始化事件监听器
     */
    initEventListeners() {
        // 编码功能
        this.encodeBtn.addEventListener('click', () => this.handleEncode());
        this.clearTextBtn.addEventListener('click', () => this.clearTextInputs());
        this.copyEncodedBtn.addEventListener('click', () => this.copyToClipboard(this.encodedOutput.value, '编码结果已复制'));
        
        // 解码功能
        this.decodeBtn.addEventListener('click', () => this.handleDecode());
        this.clearBase64Btn.addEventListener('click', () => this.clearBase64Inputs());
        this.copyDecodedBtn.addEventListener('click', () => this.copyToClipboard(this.decodedOutput.value, '解码结果已复制'));
        
        // 文件处理功能
        this.encodeFileBtn.addEventListener('click', () => this.handleFileEncode());
        this.copyFileResultBtn.addEventListener('click', () => this.copyToClipboard(this.fileOutput.value, '文件结果已复制'));
        this.downloadResultBtn.addEventListener('click', () => this.downloadResult());
        
        // 实时输入处理
        this.textInput.addEventListener('input', () => {
            this.updateCharCount(this.textInput, this.textCharCount);
            this.handleRealTimeEncode();
        });
        this.base64Input.addEventListener('input', () => {
            this.updateCharCount(this.base64Input, this.base64CharCount);
            this.handleRealTimeDecode();
        });
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
        
        // 文件选择变化
        this.fileInput.addEventListener('change', () => this.handleFileSelection());
        
        // 拖拽区域点击
        this.dragDropArea.addEventListener('click', () => this.fileInput.click());
        
        // 选择文件按钮
        const selectFileBtn = document.querySelector('.btn-select-file');
        if (selectFileBtn) {
            selectFileBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.fileInput.click();
            });
        }
    }
    
    /**
     * 设置拖拽上传功能
     */
    setupDragAndDrop() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dragDropArea.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            this.dragDropArea.addEventListener(eventName, () => this.dragDropArea.classList.add('drag-over'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            this.dragDropArea.addEventListener(eventName, () => this.dragDropArea.classList.remove('drag-over'), false);
        });
        
        this.dragDropArea.addEventListener('drop', (e) => this.handleFileDrop(e), false);
    }
    
    /**
     * 阻止默认拖拽行为
     */
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    /**
     * 处理文件拖拽放置
     */
    handleFileDrop(e) {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.fileInput.files = files;
            this.handleFileSelection();
        }
    }
    
    /**
     * 处理编码请求
     */
    async handleEncode() {
        const text = this.textInput.value;
        
        if (!text.trim()) {
            this.showNotification('请输入要编码的文本', 'error');
            return;
        }
        
        this.setButtonLoading(this.encodeBtn, true);
        this.clearInputState(this.textInput);
        
        try {
            const result = await this.encodeText(text);
            this.encodedOutput.value = result;
            this.setInputState(this.textInput, 'success');
            this.showNotification('编码成功', 'success');
        } catch (error) {
            this.setInputState(this.textInput, 'error');
            this.showNotification(`编码失败: ${error.message}`, 'error');
            console.error('Encode error:', error);
        } finally {
            this.setButtonLoading(this.encodeBtn, false);
        }
    }
    
    /**
     * 处理解码请求
     */
    async handleDecode() {
        const base64String = this.base64Input.value;
        
        if (!base64String.trim()) {
            this.showNotification('请输入要解码的Base64字符串', 'error');
            return;
        }
        
        this.setButtonLoading(this.decodeBtn, true);
        this.clearInputState(this.base64Input);
        
        try {
            const result = await this.decodeBase64(base64String);
            this.decodedOutput.value = result;
            this.setInputState(this.base64Input, 'success');
            this.showNotification('解码成功', 'success');
        } catch (error) {
            this.setInputState(this.base64Input, 'error');
            this.showNotification(`解码失败: ${error.message}`, 'error');
            console.error('Decode error:', error);
        } finally {
            this.setButtonLoading(this.decodeBtn, false);
        }
    }
    
    /**
     * 处理实时编码
     */
    async handleRealTimeEncode() {
        const text = this.textInput.value;
        
        if (!text) {
            this.encodedOutput.value = '';
            this.clearInputState(this.textInput);
            return;
        }
        
        // 检查文本长度
        if (text.length > 100000) {
            this.encodedOutput.value = '';
            this.setInputState(this.textInput, 'error');
            this.showNotification('文本过长，请输入少于100,000个字符的文本', 'error');
            return;
        }
        
        try {
            const result = await this.encodeText(text);
            this.encodedOutput.value = result;
            this.setInputState(this.textInput, 'success');
        } catch (error) {
            this.encodedOutput.value = '';
            this.setInputState(this.textInput, 'error');
        }
    }
    
    /**
     * 处理实时解码
     */
    async handleRealTimeDecode() {
        const base64String = this.base64Input.value.trim();
        
        if (!base64String) {
            this.decodedOutput.value = '';
            this.clearInputState(this.base64Input);
            return;
        }
        
        // 基本的Base64格式验证
        if (!this.isValidBase64Format(base64String)) {
            this.decodedOutput.value = '';
            this.setInputState(this.base64Input, 'error');
            return;
        }
        
        try {
            const result = await this.decodeBase64(base64String);
            this.decodedOutput.value = result;
            this.setInputState(this.base64Input, 'success');
        } catch (error) {
            this.decodedOutput.value = '';
            this.setInputState(this.base64Input, 'error');
        }
    }
    
    /**
     * 处理文件编码
     */
    async handleFileEncode() {
        const file = this.fileInput.files[0];
        
        if (!file) {
            this.showNotification('请选择要编码的文件', 'error');
            return;
        }
        
        this.setButtonLoading(this.encodeFileBtn, true);
        this.showProgress(true, '正在读取文件...', 20);
        
        try {
            const fileContent = await this.readFileAsText(file);
            this.updateProgress(60, '正在编码...');
            
            const result = await this.encodeText(fileContent);
            this.updateProgress(100, '编码完成');
            
            this.fileOutput.value = result;
            this.showNotification(`文件 "${file.name}" 编码成功`, 'success');
            
            // 延迟隐藏进度条
            setTimeout(() => {
                this.showProgress(false);
            }, 1000);
            
        } catch (error) {
            this.showProgress(false);
            this.showNotification(`文件编码失败: ${error.message}`, 'error');
            console.error('File encode error:', error);
        } finally {
            this.setButtonLoading(this.encodeFileBtn, false);
        }
    }
    
    /**
     * 处理文件选择
     */
    handleFileSelection() {
        const file = this.fileInput.files[0];
        if (file) {
            this.selectedFileName.textContent = `${file.name} (${this.formatFileSize(file.size)})`;
            this.showNotification(`已选择文件: ${file.name}`, 'info');
        } else {
            this.selectedFileName.textContent = '';
        }
    }
    
    /**
     * 调用后端编码API
     */
    async encodeText(text) {
        const response = await fetch(`${this.apiBaseUrl}/encode`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: text })
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error?.message || '编码请求失败');
        }
        
        return data.result;
    }
    
    /**
     * 调用后端解码API
     */
    async decodeBase64(base64String) {
        const response = await fetch(`${this.apiBaseUrl}/decode`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ base64_string: base64String })
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error?.message || '解码请求失败');
        }
        
        return data.result;
    }
    
    /**
     * 读取文件内容为文本
     */
    readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(new Error('文件读取失败'));
            reader.readAsText(file, 'UTF-8');
        });
    }
    
    /**
     * 复制文本到剪贴板
     */
    async copyToClipboard(text, successMessage = '已复制到剪贴板') {
        if (!text) {
            this.showNotification('没有内容可复制', 'error');
            return;
        }
        
        try {
            await navigator.clipboard.writeText(text);
            this.showNotification(successMessage, 'success');
        } catch (error) {
            // 降级方案：使用传统方法
            this.fallbackCopyToClipboard(text);
            this.showNotification(successMessage, 'success');
        }
    }
    
    /**
     * 降级复制方法
     */
    fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
        } catch (error) {
            console.error('Fallback copy failed:', error);
        }
        
        document.body.removeChild(textArea);
    }
    
    /**
     * 下载结果文件
     */
    downloadResult() {
        const content = this.fileOutput.value;
        
        if (!content) {
            this.showNotification('没有内容可下载', 'error');
            return;
        }
        
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'base64_result.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('文件下载已开始', 'success');
    }
    
    /**
     * 清空文本输入
     */
    clearTextInputs() {
        this.textInput.value = '';
        this.encodedOutput.value = '';
        this.clearInputState(this.textInput);
        this.updateCharCount(this.textInput, this.textCharCount);
    }
    
    /**
     * 清空Base64输入
     */
    clearBase64Inputs() {
        this.base64Input.value = '';
        this.decodedOutput.value = '';
        this.clearInputState(this.base64Input);
        this.updateCharCount(this.base64Input, this.base64CharCount);
    }
    
    /**
     * 设置按钮加载状态
     */
    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            button.classList.add('loading');
            button.dataset.originalText = button.textContent;
            button.textContent = '处理中...';
        } else {
            button.disabled = false;
            button.classList.remove('loading');
            button.textContent = button.dataset.originalText || button.textContent;
        }
    }
    
    /**
     * 设置输入框状态
     */
    setInputState(input, state) {
        input.classList.remove('error-input', 'success-input');
        if (state === 'error') {
            input.classList.add('error-input');
        } else if (state === 'success') {
            input.classList.add('success-input');
        }
    }
    
    /**
     * 清除输入框状态
     */
    clearInputState(input) {
        input.classList.remove('error-input', 'success-input');
    }
    
    /**
     * 显示通知
     */
    showNotification(message, type = 'info', duration = 3000) {
        this.notification.textContent = message;
        this.notification.className = `notification ${type}`;
        this.notification.classList.remove('hidden');
        
        setTimeout(() => {
            this.notification.classList.add('hidden');
        }, duration);
    }
    
    /**
     * 处理键盘快捷键
     */
    handleKeyboardShortcuts(e) {
        // Ctrl+Enter 或 Cmd+Enter 执行编码
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            if (document.activeElement === this.textInput) {
                this.handleEncode();
            } else if (document.activeElement === this.base64Input) {
                this.handleDecode();
            }
        }
        
        // Escape 清空当前输入
        if (e.key === 'Escape') {
            if (document.activeElement === this.textInput) {
                this.clearTextInputs();
            } else if (document.activeElement === this.base64Input) {
                this.clearBase64Inputs();
            }
        }
    }
    
    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    /**
     * 验证Base64格式
     */
    isValidBase64Format(str) {
        // Base64字符集：A-Z, a-z, 0-9, +, /, =
        const base64Regex = /^[A-Za-z0-9+/]*={0,2}$/;
        
        // 检查基本格式
        if (!base64Regex.test(str)) {
            return false;
        }
        
        // 检查长度（必须是4的倍数）
        if (str.length % 4 !== 0) {
            return false;
        }
        
        // 检查填充字符位置
        const paddingIndex = str.indexOf('=');
        if (paddingIndex !== -1) {
            // 填充字符只能在末尾
            const padding = str.substring(paddingIndex);
            if (padding !== '=' && padding !== '==') {
                return false;
            }
            // 填充字符后不能有其他字符
            if (str.substring(0, paddingIndex).includes('=')) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * 更新字符计数
     */
    updateCharCount(input, countElement) {
        const count = input.value.length;
        countElement.textContent = `${count.toLocaleString()} 字符`;
        
        // 根据字符数量改变颜色
        if (count > 50000) {
            countElement.style.color = '#e74c3c';
        } else if (count > 10000) {
            countElement.style.color = '#f39c12';
        } else {
            countElement.style.color = '#3498db';
        }
    }
    
    /**
     * 显示/隐藏进度条
     */
    showProgress(show, text = '处理中...', progress = 0) {
        if (show) {
            this.fileProgress.classList.remove('hidden');
            this.progressText.textContent = text;
            this.progressFill.style.width = `${progress}%`;
        } else {
            this.fileProgress.classList.add('hidden');
        }
    }
    
    /**
     * 更新进度条
     */
    updateProgress(progress, text) {
        this.progressFill.style.width = `${progress}%`;
        this.progressText.textContent = text;
    }
    
    /**
     * 加载示例数据
     */
    loadExample(type, data) {
        if (type === 'encode') {
            this.textInput.value = data;
            this.updateCharCount(this.textInput, this.textCharCount);
            this.textInput.focus();
            this.handleRealTimeEncode();
            this.showNotification('示例已加载到编码区域', 'info');
        } else if (type === 'decode') {
            this.base64Input.value = data;
            this.updateCharCount(this.base64Input, this.base64CharCount);
            this.base64Input.focus();
            this.handleRealTimeDecode();
            this.showNotification('示例已加载到解码区域', 'info');
        }
    }
}

// 全局应用实例
let app;

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    app = new Base64WebClient();
    
    // 添加一些使用提示
    console.log('Base64 Web Client 已加载');
    console.log('快捷键:');
    console.log('  Ctrl+Enter: 执行编码/解码');
    console.log('  Escape: 清空当前输入');
    console.log('支持拖拽文件到文件处理区域');
});

// 全局函数供HTML调用
function loadExample(type, data) {
    if (app) {
        app.loadExample(type, data);
    }
}

// 导出类以便测试
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Base64WebClient;
}