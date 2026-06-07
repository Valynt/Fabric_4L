// ValuePact Documentation enhancements

document.addEventListener('DOMContentLoaded', function () {
  // Add copy-to-clipboard for code blocks without built-in copy
  const codeBlocks = document.querySelectorAll('pre > code:not(.hljs)');
  codeBlocks.forEach(function (block) {
    if (!block.parentElement.querySelector('.md-clipboard')) {
      const pre = block.parentElement;
      pre.classList.add('md-code__block');
    }
  });

  // Auto-expand admonition titles on hover for long titles
  const admonitions = document.querySelectorAll('.admonition');
  admonitions.forEach(function (adm) {
    adm.classList.add('admonition--enhanced');
  });
});
