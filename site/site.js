// Reading and navigation work without JavaScript; this only adds copy controls.
const chinese = document.documentElement.lang === 'zh-CN';
document.querySelectorAll('pre > code').forEach(code => {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'copy';
  button.textContent = chinese ? '复制' : 'Copy';
  const status = document.createElement('span');
  status.className = 'copy-status';
  status.setAttribute('aria-live', 'polite');
  code.parentElement.before(button, status);
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(code.textContent);
      status.textContent = chinese ? '已复制' : 'Copied';
    } catch {
      status.textContent = chinese ? '请选中代码并手动复制' : 'Select the code and copy manually';
    }
  });
});
