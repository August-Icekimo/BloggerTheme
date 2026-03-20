/**
 * Obfuscated Block #1 — Dark Mode & Letter Initialization
 * ========================================================
 * 
 * Source: Igniplex v3.1.xml, line 188-190
 * Location: <head> section, inside <script>//[CDATA[ ... ]]</script>
 * Packer: Dean Edwards Packer (eval(function(p,a,c,k,e,d){...}))
 * 
 * Purpose:
 *   This script reads saved user preferences from localStorage and applies
 *   them to the <html> element on page load, BEFORE the CSS is parsed.
 *   This prevents a "flash of unstyled content" (FOUC) when switching
 *   between light/dark mode or different letter styles.
 * 
 * Risk Level: LOW (no external requests, no redirects)
 */

// ===== DEOBFUSCATED CODE =====

function _0x308c() {
  const _0x387c96 = [
    '331941aDfgUd', '1975730wfkgev', '1400823qhssEq', '11522EMyRAe',
    '499332Jwuouj', 'dark', 'html', '1234816hsAfct', 'data-letter',
    'setAttribute', '22AxjADx', 'igniel-', '70wXlTwA', 'data-blog',
    'getAttribute', 'parse', 'letter', '1478925UVfjzY', '4QFZbwy',
    '5UQbIwD'
  ];
  _0x308c = function () { return _0x387c96; };
  return _0x308c();
}

// (Anti-tamper shuffle loop omitted for clarity)

// Main logic:
const first = document.documentElement || document.getElementsByTagName('html')[0];
const bID = first.getAttribute('data-blog');

// Read saved preferences from localStorage using key "igniel-{blogId}"
let ign = JSON.parse(localStorage.getItem('igniel-' + bID)) || {};

// Apply preferences immediately:
(() => {
  // If "dark" key exists in saved prefs, set data-theme="dark" on <html>
  if ('dark' in ign) {
    first.setAttribute('data-theme', 'dark');
  }

  // If "letter" key exists in saved prefs, set data-letter attribute on <html>
  if ('letter' in ign) {
    first.setAttribute('data-letter', ign['letter']);
  }
})();
