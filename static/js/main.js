// 主要JavaScript文件
document.addEventListener('DOMContentLoaded', function() {
    // 初始化Bootstrap组件
    initBootstrapComponents();
    
    // 为导航项设置激活状态
    setActiveNavItem();
    
    // 为反馈按钮绑定事件
    bindFeedbackButton();
});

/**
 * 初始化Bootstrap组件
 */
function initBootstrapComponents() {
    // 初始化提示工具
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 初始化弹出框
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // 初始化侧边栏折叠
    var sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.body.classList.toggle('sidebar-collapsed');
            
            // 保存状态到localStorage
            var sidebarCollapsed = document.body.classList.contains('sidebar-collapsed');
            localStorage.setItem('sidebar-collapsed', sidebarCollapsed);
        });
        
        // 从localStorage中恢复侧边栏状态
        var sidebarCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
        if (sidebarCollapsed) {
            document.body.classList.add('sidebar-collapsed');
        }
    }
    
    // 移动设备上自动折叠侧边栏
    if (window.innerWidth < 768) {
        document.body.classList.add('sidebar-collapsed');
    }
    
    // 主题切换
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            // 切换主题
            document.documentElement.setAttribute('data-bs-theme', newTheme);
            
            // 更新图标
            const themeIcon = this.querySelector('i');
            if (themeIcon) {
                themeIcon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            }
            
            // 保存主题设置
            localStorage.setItem('theme', newTheme);
        });
        
        // 从localStorage加载主题设置
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-bs-theme', savedTheme);
            
            // 更新图标
            const themeIcon = themeToggle.querySelector('i');
            if (themeIcon) {
                themeIcon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            }
        }
    }
}

/**
 * 设置当前导航项的激活状态
 */
function setActiveNavItem() {
    // 获取当前路径
    var path = window.location.pathname;
    
    // 查找对应的导航项
    var navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(function(link) {
        var href = link.getAttribute('href');
        
        // 简单路径匹配(非精确匹配)
        if (href === path || (href !== '/' && path.startsWith(href))) {
            link.classList.add('active');
            
            // 如果在侧边栏中，展开父菜单
            var parentCollapse = link.closest('.collapse');
            if (parentCollapse) {
                parentCollapse.classList.add('show');
                var trigger = document.querySelector('[data-bs-target="#' + parentCollapse.id + '"]');
                if (trigger) {
                    trigger.classList.remove('collapsed');
                    trigger.setAttribute('aria-expanded', 'true');
                }
            }
        }
    });
}

/**
 * 绑定反馈按钮事件
 */
function bindFeedbackButton() {
    const feedbackBtn = document.getElementById('feedbackButton');
    const feedbackForm = document.getElementById('feedbackForm');
    
    if (feedbackBtn && feedbackForm) {
        feedbackForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const feedbackText = document.getElementById('feedbackText').value;
            const feedbackType = document.querySelector('input[name="feedbackType"]:checked').value;
            
            if (!feedbackText.trim()) {
                alert('请输入反馈内容');
                return;
            }
            
            // 发送反馈
            fetch('/api/submit-feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: feedbackText,
                    type: feedbackType
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 清空表单
                    document.getElementById('feedbackText').value = '';
                    
                    // 关闭模态框
                    const modal = bootstrap.Modal.getInstance(document.getElementById('feedbackModal'));
                    modal.hide();
                    
                    // 显示成功消息
                    showAlert('感谢您的反馈！', 'success');
                } else {
                    showAlert('提交反馈时出错，请稍后再试。', 'danger');
                }
            })
            .catch(error => {
                console.error('提交反馈时发生错误:', error);
                showAlert('提交反馈时发生错误，请稍后再试。', 'danger');
            });
        });
    }
}

/**
 * 显示警报消息
 */
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // 5秒后自动关闭
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
}