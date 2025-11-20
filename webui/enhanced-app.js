/* Combined content of enhanced-app.js (lines 1-643) */
/**
 * 增强版前端应用 - 集成后端API
 */

// API配置
const API_BASE = 'http://127.0.0.1:8010';

// 应用状态
let appState = {
    licenseKey: '',
    licenseStatus: '未激活',
    machineHash: '',
    isActivated: false,
    scrapingActive: false,
    sessionToken: null,
    licenseId: null
};

// DOM元素缓存
const elements = {};

// 初始化应用
document.addEventListener('DOMContentLoaded', function() {
    // Bind disclaimer events immediately
    bindDisclaimerEvents();
    // Show disclaimer first
    showDisclaimer();
});

// 缓存DOM元素
function cacheElements() {
    elements.kw = document.getElementById('kw');
    elements.price = document.getElementById('price');
    elements.pinned = document.getElementById('pinned');
    elements.reviews = document.getElementById('reviews');
    elements.exportDir = document.getElementById('exportDir');
    elements.pickBtn = document.getElementById('pickBtn');
    elements.startBtn = document.getElementById('startBtn');
    elements.stopBtn = document.getElementById('stopBtn');
    elements.licCode = document.getElementById('licCode');
    elements.activateBtn = document.getElementById('activateBtn');
    elements.machine = document.getElementById('machine');
    elements.licStatus = document.getElementById('licStatus');
    elements.remain = document.getElementById('remain');
    elements.nowList = document.getElementById('nowList');
    elements.cardList = document.getElementById('cardList');
    elements.mCollected = document.getElementById('m_collected');
    elements.mAvgPrice = document.getElementById('m_avg_price');
    elements.mAvgPinned = document.getElementById('m_avg_pinned');
    elements.resultBox = document.getElementById('resultBox');
    elements.badgeCnt = document.getElementById('badgeCnt');
    elements.exportBtn = document.getElementById('exportBtn');
    elements.openBtn = document.getElementById('openBtn');
    elements.copyMachineBtn = document.getElementById('copyMachineBtn');
}

// 绑定免责声明事件（独立于主应用）
function bindDisclaimerEvents() {
    const acceptCheckbox = document.getElementById('acceptDisclaimer');
    const acceptBtn = document.getElementById('acceptBtn');
    const declineBtn = document.getElementById('declineBtn');
    const modalBody = document.querySelector('.modal-body');
    
    logDebug('绑定免责声明事件...');
    
    if (acceptCheckbox && acceptBtn && declineBtn && modalBody) {
        logDebug('所有必需元素都存在');
        
        // 初始状态：同意按钮禁用，不同意按钮可用
        acceptBtn.disabled = true;
        declineBtn.disabled = false;
        
        logDebug(`初始状态 - 同意按钮: ${acceptBtn.disabled ? '禁用' : '启用'}, 不同意按钮: ${declineBtn.disabled ? '禁用' : '启用'}`);
        
        // 检查是否已经滚动到底部
        function checkScrollBottom() {
            try {
                const scrollBottom = modalBody.scrollTop + modalBody.clientHeight;
                const scrollHeight = modalBody.scrollHeight;
                const isBottom = scrollBottom >= scrollHeight - 10; // 10px容错
                
                // 只有在滚动到底部且复选框勾选时，才启用同意按钮
                const shouldEnable = isBottom && acceptCheckbox.checked;
                acceptBtn.disabled = !shouldEnable;
                
                logDebug(`滚动检查 - 位置: ${Math.round((modalBody.scrollTop / (scrollHeight - modalBody.clientHeight)) * 100)}%, 底部: ${isBottom ? '是' : '否'}, 复选框: ${acceptCheckbox.checked ? '勾选' : '未勾选'}, 同意按钮: ${acceptBtn.disabled ? '禁用' : '启用'}`);
                
                // 显示/隐藏滚动指示器
                const scrollIndicator = document.getElementById('scrollIndicator');
                if (scrollIndicator) {
                    scrollIndicator.style.display = isBottom ? 'none' : 'block';
                }
            } catch (error) {
                logDebug(`滚动检查错误: ${error.message}`, 'error');
            }
        }
        
        // 绑定事件监听器
        try {
            modalBody.addEventListener('scroll', checkScrollBottom);
            acceptCheckbox.addEventListener('change', checkScrollBottom);
            acceptBtn.addEventListener('click', acceptDisclaimer);
            declineBtn.addEventListener('click', declineDisclaimer);
            
            logDebug('事件监听器绑定成功');
            
            // 初始检查（延迟确保内容加载完成）
            setTimeout(() => {
                checkScrollBottom();
                logDebug('初始滚动检查完成');
            }, 500);
            
        } catch (error) {
            logDebug(`事件绑定错误: ${error.message}`, 'error');
        }
        
    } else {
        logDebug('缺少必需元素:', 'error');
        if (!acceptCheckbox) logDebug('- 复选框不存在', 'error');
        if (!acceptBtn) logDebug('- 同意按钮不存在', 'error');
        if (!declineBtn) logDebug('- 不同意按钮不存在', 'error');
        if (!modalBody) logDebug('- 模态框内容区域不存在', 'error');
    }
}

// 绑定主应用事件
function bindEvents() {
    elements.pickBtn.addEventListener('click', pickDirectory);
    elements.startBtn.addEventListener('click', startScraping);
    elements.stopBtn.addEventListener('click', stopScraping);
    elements.activateBtn.addEventListener('click', activateLicense);
    elements.exportBtn.addEventListener('click', exportResults);
    elements.openBtn.addEventListener('click', openFolder);
    if (elements.exportDir) {
        elements.exportDir.addEventListener('input', toggleExportTip);
        elements.exportDir.addEventListener('change', toggleExportTip);
    }
    if (elements.copyMachineBtn) {
        elements.copyMachineBtn.addEventListener('click', copyMachineCode);
    }
}

// 加载初始状态
async function loadInitialState() {
    try {
        let machineHash = '';
        if (window.pywebview && window.pywebview.api && window.pywebview.api.getMachineHash) {
            machineHash = await window.pywebview.api.getMachineHash();
        } else {
            const saved = localStorage.getItem('machineCode');
            if (saved) {
                machineHash = saved;
            } else {
                const src = (navigator.userAgent || '') + (screen.width || '') + (screen.height || '') + (new Date().getTimezoneOffset());
                let h = 0;
                for (let i = 0; i < src.length; i++) {
                    h = ((h << 5) - h) + src.charCodeAt(i);
                    h |= 0;
                }
                machineHash = 'MC-' + Math.abs(h).toString(16).padStart(8, '0');
                localStorage.setItem('machineCode', machineHash);
            }
        }
        appState.machineHash = machineHash;
        elements.machine.textContent = `机器码：${machineHash}`;
        
        // 获取应用状态
        const state = await window.pywebview.api.getState();
        if (state) {
            elements.kw.value = state.keyword || '';
            elements.price.value = state.price || '';
            elements.pinned.value = state.pinned || '';
            elements.reviews.value = state.reviews || '';
            if (state.exportDir) {
                elements.exportDir.value = state.exportDir;
                toggleExportTip();
            }
            updateStatus(state.status);
        }
        
        // 验证现有许可证 - simplified for customer interface
        try {
            const result = await window.pywebview.api.validate();
            if (result.status === 'OK') {
                appState.licenseId = result.license_id;
                appState.sessionToken = result.session_token;
                appState.isActivated = true;
                appState.licenseStatus = '已激活';
                
                elements.licStatus.textContent = `状态：已激活`;
                const expiresAt = result.expires_at ? new Date(result.expires_at) : null;
                if (expiresAt) {
                    const remainTime = expiresAt - new Date();
                    const days = Math.floor(remainTime / (1000 * 60 * 60 * 24));
                    elements.remain.textContent = `剩余：${days} 天`;
                }
            } else if (result.status === 'EXPIRED') {
                appState.isActivated = false;
                appState.licenseStatus = '已过期';
                elements.licStatus.textContent = `状态：已过期`;
                elements.remain.textContent = `剩余：0 天`;
            }
        } catch (error) {
            console.log('许可证验证失败:', error);
        }
        
    } catch (error) {
        console.error('加载初始状态失败:', error);
        showMessage('加载初始状态失败', 'error');
    }
}

// 心跳机制
function startHeartbeat() {
    setInterval(async () => {
        if (appState.sessionToken && appState.licenseId) {
            try {
                await fetch(`${API_BASE}/sessions/heartbeat`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        license_id: appState.licenseId,
                        machine_hash: appState.machineHash,
                        session_token: appState.sessionToken
                    })
                });
            } catch (error) {
                console.error('心跳失败:', error);
            }
        }
    }, 30000); // 30秒心跳
}

// 选择目录
async function pickDirectory() {
    try {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.pickDirectory) {
            const result = await window.pywebview.api.pickDirectory();
            if (result.status === 'OK') {
                elements.exportDir.value = result.path;
                showMessage('导出路径设置成功', 'success');
                toggleExportTip();
                return;
            }
            showMessage('设置导出路径失败' + (result.message ? ': ' + result.message : ''), 'error');
            return;
        }
        showMessage('当前为浏览器环境，无法选择导出路径。请在EXE客户端中设置导出目录。', 'warning');
    } catch (error) {
        showMessage('设置导出路径失败', 'error');
    }
}

// 激活许可证
async function activateLicense() {
    const licenseKey = elements.licCode.value.trim();
    if (!licenseKey) {
        showMessage('请输入激活码', 'warning');
        return;
    }
    
    try {
        showMessage('正在激活...', 'info');
        const result = await window.pywebview.api.activate(licenseKey);
        
        if (result.status === 'OK') {
            appState.licenseKey = licenseKey;
            appState.licenseId = result.license_id;
            appState.isActivated = true;
            appState.licenseStatus = '已激活';
            
            elements.licStatus.textContent = `状态：已激活`;
            const expiresAt = result.expires_at ? new Date(result.expires_at) : null;
            if (expiresAt) {
                const remainTime = expiresAt - new Date();
                const days = Math.floor(remainTime / (1000 * 60 * 60 * 24));
                elements.remain.textContent = `剩余：${days} 天`;
            }
            
            showMessage('激活成功！', 'success');
            // Auto-validate after successful activation - simplified for customer interface
        } else {
            let message = '激活失败';
            switch (result.status) {
                case 'INVALID':
                    message = '激活码无效';
                    break;
                case 'BOUND_OTHER':
                    message = '激活码已绑定其他设备';
                    break;
                case 'ERROR':
                    message = '激活错误: ' + (result.message || '');
                    break;
            }
            showMessage(message, 'error');
        }
    } catch (error) {
        console.error('激活失败:', error);
        showMessage('激活失败: ' + error.message, 'error');
    }
}

// Customer interface - simplified license validation removed

// 开始采集
async function startScraping() {
    if (!appState.isActivated) {
        showMessage('请先激活软件', 'warning');
        return;
    }
    
    const params = {
        keyword: elements.kw.value.trim(),
        price: parseFloat(elements.price.value) || 0,
        pinned: parseInt(elements.pinned.value) || 0,
        reviews: parseInt(elements.reviews.value) || 0,
        exportDir: elements.exportDir.value
    };
    
    if (!params.keyword) {
        showMessage('请输入商品关键词', 'warning');
        return;
    }
    
    if (!params.exportDir) {
        showMessage('请选择导出目录', 'warning');
        return;
    }
    
    try {
        showMessage('正在启动采集...', 'info');
        const result = await window.pywebview.api.startScrape(params);
        
        if (result.status === 'OK') {
            appState.scrapingActive = true;
            elements.startBtn.disabled = true;
            elements.stopBtn.disabled = false;
            showMessage('采集已开始', 'success');
            
            // 设置采集状态回调
            window.__onProgress = function(data) {
                updateProgress(data);
            };
            
            window.__onItem = function(item) {
                addResultItem(item);
            };
            
            window.__onStatus = function(status) {
                updateStatus(status);
                if (status === 'idle') {
                    appState.scrapingActive = false;
                    elements.startBtn.disabled = false;
                    elements.stopBtn.disabled = true;
                    showMessage('采集已完成', 'success');
                }
            };
            
        } else {
            let message = '启动采集失败';
            switch (result.status) {
                case 'NO_KEY':
                    message = '未找到激活码';
                    break;
                case 'NO_EXPORT_DIR':
                    message = '未选择导出目录';
                    break;
                case 'ERROR':
                    message = '启动错误: ' + (result.message || '');
                    break;
            }
            showMessage(message, 'error');
        }
    } catch (error) {
        console.error('启动采集失败:', error);
        showMessage('启动采集失败: ' + error.message, 'error');
    }
}

// 停止采集
async function stopScraping() {
    try {
        const result = await window.pywebview.api.stopScrape();
        if (result.status === 'OK') {
            appState.scrapingActive = false;
            elements.startBtn.disabled = false;
            elements.stopBtn.disabled = true;
            showMessage('采集已停止', 'success');
        } else {
            showMessage('停止采集失败', 'error');
        }
    } catch (error) {
        console.error('停止采集失败:', error);
        showMessage('停止采集失败', 'error');
    }
}

// 更新进度
function updateProgress(data) {
    const progressText = `已访:${data.visited || 0} | 采:${data.collected || 0} | 过:${data.filtered || 0}`;
    appendNowLine(progressText);
    if (elements.mCollected) {
        elements.mCollected.textContent = data.collected || 0;
    }
    if (elements.mAvgPrice) {
        elements.mAvgPrice.textContent = data.avg_price ? `¥${Number(data.avg_price).toFixed(2)}` : '--';
    }
    if (elements.mAvgPinned) {
        elements.mAvgPinned.textContent = data.avg_pinned ? `${Number(data.avg_pinned).toFixed(0)}` : '--';
    }
}

// 添加结果项
function addResultItem(item) {
    const list = elements.cardList;
    if (list) {
        const idx = list.children.length + 1;
        const title = (item.title || '').toString().slice(0, 10);
        const price = item.price || 0;
        const pinned = item.pinned || 0;
        const reviews = item.reviews || 0;
        const url = item.url || '';
        const card = document.createElement('div');
        card.className = 'itemCard';
        card.innerHTML = `
            <div class="index">${idx}</div>
            <div class="meta">${title}</div>
            <div class="price">¥${price}</div>
            <div>拼单:${pinned}</div>
            <div>评价:${reviews}</div>
        `;
        list.insertBefore(card, list.firstChild);
        while (list.children.length > 50) {
            list.removeChild(list.lastChild);
        }
        appendNowLine(`${title} | ¥${price} | 拼:${pinned} | 评:${reviews}`);
    }
    if (elements.resultBox) {
        const row = document.createElement('div');
        row.className = 'resultRow';
        const title = (item.title || '未知商品').toString();
        row.innerHTML = `
            <div class="title">${item.url ? `<a href="${item.url}" target="_blank">${title}</a>` : title}</div>
            <div class="price">¥${item.price || 0}</div>
            <div class="pinned">${item.pinned || 0}</div>
            <div class="reviews">${item.reviews || 0}</div>
        `;
        elements.resultBox.insertBefore(row, elements.resultBox.firstChild);
        while (elements.resultBox.children.length > 200) {
            elements.resultBox.removeChild(elements.resultBox.lastChild);
        }
        if (elements.badgeCnt) {
            const current = Number(elements.mCollected ? elements.mCollected.textContent : 0) || 0;
            elements.badgeCnt.textContent = `已采集：${current} 条数据`;
        }
    }
}

// 更新状态
function updateStatus(status) {
    appendNowLine(status === 'idle' ? '待机中…' : `状态: ${status}`);
}

// 导出结果
async function exportResults() {
    try {
        const result = await window.pywebview.api.getState();
        if (result.outfile) {
            showMessage(`结果已导出到: ${result.outfile}`, 'success');
        } else {
            showMessage('暂无导出文件', 'info');
        }
    } catch (error) {
        showMessage('获取导出文件失败', 'error');
    }
}

// 打开文件夹
async function openFolder() {
    try {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.openFolder) {
            const result = await window.pywebview.api.openFolder();
            if (result.status === 'OK') {
                showMessage('已打开文件夹', 'success');
            } else {
                showMessage('打开文件夹失败' + (result.message ? ': ' + result.message : ''), 'error');
            }
            return;
        }
        showMessage('后端未集成打开目录功能', 'info');
    } catch (error) {
        showMessage('打开文件夹失败', 'error');
    }
}

// 显示消息
function showMessage(message, type = 'info') {
    // 创建消息提示
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 3000);
    
    // 点击移除
    messageDiv.addEventListener('click', () => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    });
}

// 调试日志功能
function logDebug(message, type = 'info') {
    return;
}

// 免责声明功能
function showDisclaimer() {
    logDebug('显示免责声明模态框');
    // Check if user has already accepted disclaimer
    const disclaimerAccepted = localStorage.getItem('disclaimerAccepted');
    if (disclaimerAccepted === 'true') {
        logDebug('用户已接受免责声明，跳过显示');
        // User has already accepted, proceed with normal initialization
        initializeApp();
        return;
    }
    
    // Show disclaimer modal
    const modal = document.getElementById('disclaimerModal');
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // Prevent scrolling
        logDebug('免责声明模态框已显示');
    } else {
        logDebug('错误：找不到免责声明模态框元素');
    }
}

function acceptDisclaimer() {
    logDebug('用户点击接受免责声明');
    try {
        // Store acceptance in localStorage
        localStorage.setItem('disclaimerAccepted', 'true');
        localStorage.setItem('disclaimerAcceptedDate', new Date().toISOString());
        logDebug('免责声明接受状态已保存');
        
        // Hide modal
        const modal = document.getElementById('disclaimerModal');
        if (modal) {
            modal.style.display = 'none';
            logDebug('模态框已隐藏');
        }
        document.body.style.overflow = ''; // Restore scrolling
        
        // Proceed with app initialization
        logDebug('开始初始化应用程序');
        initializeApp();
    } catch (error) {
        logDebug(`接受免责声明时出错: ${error.message}`, 'error');
        alert('接受免责声明时出错');
    }
}

function declineDisclaimer() {
    logDebug('用户点击拒绝免责声明');
    try {
        // Exit the application
        if (window.pywebview && window.pywebview.api) {
            logDebug('调用PyWebView退出函数');
            window.pywebview.api.exitApp();
        } else {
            alert('您必须同意免责声明才能使用本软件');
            document.body.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100vh;font-size:18px;color:#666;">软件已退出</div>';
        }
    } catch (error) {
        logDebug(`拒绝免责声明时出错: ${error.message}`, 'error');
        alert('退出软件时出错，请手动关闭窗口。');
    }
}

function initializeApp() {
    // Cache elements and bind events
    cacheElements();
    bindEvents();
    
    // Load initial state and start heartbeat
    loadInitialState();
    startHeartbeat();
}

async function copyMachineCode() {
    try {
        const text = appState.machineHash || (elements.machine ? elements.machine.textContent.replace('机器码：', '').trim() : '');
        if (!text) return;
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
            showMessage('已复制机器码', 'success');
            return;
        }
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showMessage('已复制机器码', 'success');
    } catch (e) {
        showMessage('复制失败', 'error');
    }
}

function appendNowLine(text){
    if(!elements.nowList) return;
    const line=document.createElement('div');
    line.textContent=text;
    elements.nowList.appendChild(line);
    while(elements.nowList.children.length>150){
        elements.nowList.removeChild(elements.nowList.firstChild);
    }
    elements.nowList.scrollTop=elements.nowList.scrollHeight;
}

function toggleExportTip(){
    const tip=document.getElementById('exportTip');
    if(!tip) return;
    const has=!!(elements.exportDir && elements.exportDir.value && elements.exportDir.value.trim());
    tip.style.display=has? 'none':'block';
}

// 全局函数供Python调用
window.__showMessage = showMessage;
window.__updateProgress = updateProgress;
window.__addResultItem = addResultItem;
window.__updateStatus = updateStatus;
