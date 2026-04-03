# DailyPost/data_journalist.py
"""
DataJournalist — 雙向 token ↔ HTML 翻譯引擎
所有轉換規則由 translations.yaml 驅動，本模組不含任何 token 硬編碼邏輯。
"""
import re
import yaml
import markdown
from pathlib import Path
from bs4 import BeautifulSoup

TRANSLATIONS_PATH = Path(__file__).parent / 'translations.yaml'
TRANSPARENT_BASE64 = "data:image/png;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

# GitHub Alert 類型定義 — Tabler Icons stroke 風格 inline SVG
# SVG: width=16 height=16 viewBox="0 0 24 24" stroke=currentColor fill=none aria-hidden=true
_ALERT_SVG = {
    'note': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    'tip': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26A7 7 0 0 1 12 2z"/></svg>',
    'important': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>',
    'warning': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    'caution': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
}
_ALERT_TYPES = {'NOTE', 'TIP', 'IMPORTANT', 'WARNING', 'CAUTION'}


class DataJournalist:
    def __init__(self, translations_path: Path = TRANSLATIONS_PATH):
        try:
            with open(translations_path, 'r', encoding='utf-8') as f:
                self._dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"translations.yaml parse error: {e}")
            raise SystemExit(1)
        self._tokens = self._dict.get('tokens', {})

    # ------------------------------------------------------------------ #
    #  PUSH: Markdown → HTML                                               #
    # ------------------------------------------------------------------ #

    def markdown_to_html(self, filepath: str) -> tuple[dict, str]:
        """Read .md file, apply push translations, return (frontmatter, html)."""
        import frontmatter as fm_lib  # python-frontmatter
        with open(filepath, 'r', encoding='utf-8') as f:
            post = fm_lib.load(f)

        content = post.content
        content = self._protect_code_blocks(content)
        content = self._push_tokens(content)
        content = self._push_github_alerts(content)
        content = self._restore_code_blocks(content)

        html = markdown.markdown(content, extensions=['fenced_code', 'tables'])
        html = self._push_lazy_images(html)
        return dict(post.metadata), html

    def _push_tokens(self, content: str) -> str:
        """Apply all push-direction token replacements, longest pattern first."""
        replacements = []
        for token_name, token_def in self._tokens.items():
            push_def = token_def.get('push', {})
            variants = push_def.get('variants', {})
            if not variants:
                # Single-variant token
                pattern = push_def.get('pattern', '')
                template = push_def.get('template', '')
                if pattern:
                    replacements.append((len(pattern), token_name, None, pattern, template))
            else:
                for variant_name, variant_def in variants.items():
                    pattern  = variant_def.get('pattern', '')
                    template = variant_def.get('template', '')
                    if pattern:
                        replacements.append((len(pattern), token_name, variant_name, pattern, template))

        # Sort by pattern length descending (longest first → avoid partial matches)
        replacements.sort(key=lambda x: x[0], reverse=True)

        for _, token_name, variant_name, pattern, template in replacements:
            content = self._apply_push_pattern(content, pattern, template, token_name)
        return content

    def _apply_push_pattern(self, content: str, pattern: str, template: str, token_name: str) -> str:
        """Convert a single pattern string to regex and apply substitution."""
        # Determine which params are nested_tokens (need multiline / }-permissive regex)
        token_def  = self._tokens.get(token_name, {})
        push_def   = token_def.get('push', {})
        params_def = push_def.get('params', {})
        nested_params = {
            k for k, v in params_def.items()
            if isinstance(v, dict) and v.get('type') == 'nested_tokens'
        }

        regex_pattern = re.escape(pattern)
        # Replace escaped {param} placeholders with named capture groups.
        # nested_tokens params use [\s\S]+? so they match newlines and } chars;
        # regular params use [^}|\n]+? (the original safe constraint).
        def _make_group(m: re.Match) -> str:
            name = m.group(1)
            if name in nested_params:
                return f'(?P<{name}>[\\s\\S]+?)'   # multiline, allows }
            return f'(?P<{name}>[^}}|\\n]+?)'        # original: no } or newline

        regex_pattern = re.sub(r'\\\{(\w+)\\\}', _make_group, regex_pattern)

        try:
            def replacer(match):
                params   = match.groupdict()
                rendered = template

                # Recursively expand nested token content before rendering
                for p_name, p_meta in params_def.items():
                    if isinstance(p_meta, dict) and p_meta.get('type') == 'nested_tokens':
                        if p_name in params:
                            params[p_name] = self._push_tokens(params[p_name])

                for k, v in params.items():
                    rendered = rendered.replace('{' + k + '}', v or '')
                return rendered.strip()

            content = re.sub(regex_pattern, replacer, content, flags=re.DOTALL)
        except re.error as e:
            print(f"Regex error in token {token_name}: {e}")
            pass
        return content


    def _push_lazy_images(self, html: str) -> str:
        """Convert <img src="..."> to lazy-load data-src pattern."""
        img_pat = re.compile(r'<img\s+alt="([^"]*)"\s+src="([^"]+)"\s*/?>')
        return img_pat.sub(
            rf'<img alt="\1" class="lazy" data-src="\2" src="{TRANSPARENT_BASE64}" />',
            html
        )

    def _push_github_alerts(self, content: str) -> str:
        """Pre-process GitHub Alert blockquote syntax into .markdown-alert HTML.

        Converts::
            > [!NOTE]
            > 內容文字

        Into::
            <div class="markdown-alert markdown-alert-note">
              <p class="markdown-alert-title"><svg>...</svg> NOTE</p>
              <p>內容文字</p>
            </div>

        - 五種已知類型：NOTE TIP IMPORTANT WARNING CAUTION（大小寫不敏感）
        - 未知類型不轉換，維持原始 blockquote
        - code block placeholder (CODEBLOCK_N_) 已在此前被 protect，故不受影響
        """
        # Match a full alert block: opening line + 0 or more body lines
        # Pattern: lines starting with "> " that immediately follow "> [!TYPE]"
        alert_pat = re.compile(
            r'^> \[!([A-Za-z]+)\][ ]*\n((?:> .*\n?|>[ ]*\n?)*)',
            re.MULTILINE
        )

        def _render_alert(m: re.Match) -> str:
            type_raw = m.group(1).upper()
            if type_raw not in _ALERT_TYPES:
                return m.group(0)  # 未知類型 → 保留原始

            type_lower = type_raw.lower()
            icon_svg = _ALERT_SVG[type_lower]

            # Collect body lines (strip leading "> " or "> ")
            body_raw = m.group(2)
            body_lines = []
            for line in body_raw.splitlines():
                if line.startswith('> '):
                    body_lines.append(line[2:])
                elif line.strip() == '>':
                    body_lines.append('')  # blank separator
                else:
                    body_lines.append(line)

            # Split body into paragraphs by blank lines
            paragraphs = []
            current: list[str] = []
            for bl in body_lines:
                if bl == '':
                    if current:
                        paragraphs.append(' '.join(current))
                        current = []
                else:
                    current.append(bl)
            if current:
                paragraphs.append(' '.join(current))

            body_html = '\n'.join(f'<p>{p}</p>' for p in paragraphs if p)

            return (
                f'<div class="markdown-alert markdown-alert-{type_lower}">\n'
                f'<p class="markdown-alert-title">{icon_svg} {type_raw}</p>\n'
                f'{body_html}\n'
                f'</div>'
            )

        return alert_pat.sub(_render_alert, content)

    # ------------------------------------------------------------------ #
    #  PULL: HTML → Markdown                                               #
    # ------------------------------------------------------------------ #

    # Unique marker used to protect \n in token strings from html2text whitespace normalization
    _TOKEN_NL_MARKER = '\x00\x01NK\x00\x01'

    def html_to_markdown(self, html: str) -> str:
        """Convert Blogger HTML back to Markdown with token restoration."""
        soup = BeautifulSoup(html, 'lxml')
        # Process tokens outside-in (containers before children)
        self._pull_tokens_recursive(soup)

        # html2text normalizes whitespace in text nodes, collapsing \n → space.
        # Protect \n in any NavigableString that contains token markers ({{ ... }})
        # so that multi-line sms-thread / sms-fold tokens survive html2text intact.
        from bs4 import NavigableString as BS4String
        for ns in soup.find_all(string=lambda t: t and '\n' in t and '{{' in t):
            ns.replace_with(str(ns).replace('\n', self._TOKEN_NL_MARKER))

        # Remaining HTML → Markdown via html2text
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links     = False
        h.body_width       = 0
        h.ignore_images    = False
        h.protect_links    = True
        result = h.handle(str(soup))

        # Restore protected newlines
        return result.replace(self._TOKEN_NL_MARKER, '\n')


    def _pull_tokens_recursive(self, soup: BeautifulSoup) -> None:
        """Walk tokens in outside_in order, replace matched elements with token strings."""
        for token_name, token_def in self._tokens.items():
            pull_def = token_def.get('pull', {})

            # --- 客製 handler dispatch ---
            handler = pull_def.get('handler', '')
            if handler == 'builtin_github_alerts_pull':
                selector = pull_def.get('selector', '')
                if selector:
                    for el in soup.select(selector):
                        if not el.parent:
                            continue
                        token_str = self._pull_github_alert_element(el)
                        if token_str is not None:
                            el.replace_with(token_str)
                continue

            selector = pull_def.get('selector', '')
            if not selector:
                continue

            # Simple outside-in: find all elements matching selector and process them
            for el in soup.select(selector):
                # If element was already replaced or removed, skip
                if not el.parent:
                    continue
                token_str = self._pull_element(el, token_name, token_def)
                if token_str is not None:
                    # Wrap with newlines so html2text keeps block tokens on separate lines
                    # rather than flowing them into a single inline paragraph.
                    el.replace_with(f'\n{token_str}\n')


    def _pull_element(self, el, token_name: str, token_def: dict) -> str | None:
        """Extract params from a BS4 element and render the output token string."""
        pull_def  = token_def.get('pull', {})
        push_def  = token_def.get('push', {})
        child_map = pull_def.get('child_map', {})
        params    = {}

        # --- Extract class-based params (e.g. sms-left / sms-right) ---
        class_ext = pull_def.get('class_extraction', {})
        if class_ext:
            prefix      = class_ext.get('prefix', '')
            valid_vals  = class_ext.get('valid_values', [])
            strip_pfx   = class_ext.get('strip_prefix', True)
            for cls in el.get('class', []):
                if cls.startswith(prefix):
                    val = cls[len(prefix):] if strip_pfx else cls
                    if val in valid_vals:
                        params[class_ext['param']] = val

        # --- Extract child-element params ---
        for p_name, p_def in child_map.items():
            child_sel = p_def.get('selector', '')
            source    = p_def.get('source', 'innerText')
            optional  = p_def.get('required', True) is False or p_def.get('optional', False)
            
            # If selector is null, use the element itself
            child     = el.select_one(child_sel) if child_sel else el
            
            if child is None:
                if optional:
                    params[p_name] = p_def.get('absent_value', None)
                    continue
                else:
                    return None
            
            if source == 'innerText':
                val = child.get_text(strip=True)
            elif source == 'innerHTML':
                val = child.decode_contents()
            elif source == 'nextSiblingHTML':
                # Everything after the child element within the parent
                siblings = []
                for sib in child.next_siblings:
                    siblings.append(str(sib))
                val = ''.join(siblings).strip()
            else:
                val = child.get(source, '')
            
            # Recurse if this param contains nested tokens
            if isinstance(p_def.get('type'), str) and p_def['type'] == 'nested_tokens':
                inner_soup = BeautifulSoup(val, 'lxml')
                self._pull_tokens_recursive(inner_soup)
                # Use .body.decode_contents() to get innerHTML WITHOUT lxml's
                # <html><body> wrapper that "".join(inner_soup.contents) would produce.
                val = inner_soup.body.decode_contents() if inner_soup.body else val

            
            params[p_name] = val

        # --- attr_map (direct attribute extraction, e.g. data-embed) ---
        for p_name, attr_name in pull_def.get('attr_map', {}).items():
            params[p_name] = el.get(attr_name, '')

        # --- Select which output variant to use ---
        variant_key    = self._select_pull_variant(params, pull_def, push_def)
        output_variants = pull_def.get('output_variants', {})
        output_template = pull_def.get('output', '')

        if output_variants:
            template = output_variants.get(variant_key, list(output_variants.values())[0])
        else:
            template = output_template

        # --- Render output string ---
        result = template
        for k, v in params.items():
            val = str(v) if v is not None else ''
            result = result.replace('{' + k + '}', val)
        return result

    def _select_pull_variant(self, params: dict, pull_def: dict, push_def: dict) -> str:
        """Determine which variant name to use based on variant_selection rules."""
        vs = pull_def.get('variant_selection', {})
        if not vs:
            return 'default'
        rule = vs.get('rule', '')

        if rule == 'match_present_params':
            mapping = vs.get('mapping', [])
            for condition in mapping:
                match = True
                for k, expected in condition.items():
                    if k == 'variant':
                        continue
                    # e.g. name_present: true → check params['name'] is not None
                    param_key = k.replace('_present', '')
                    is_present = params.get(param_key) not in [None, '']
                    if is_present != expected:
                        match = False
                        break
                if match:
                    return condition.get('variant', 'bare')

        elif rule == 'compare_default':
            param        = vs.get('param', '')
            default_val  = vs.get('default_value', '')
            is_default   = params.get(param) == default_val
            for condition in vs.get('mapping', []):
                if condition.get('is_default') == is_default:
                    return condition.get('variant', 'default')

        return 'bare'

    # ------------------------------------------------------------------ #
    #  GitHub Alert Pull handler                                           #
    # ------------------------------------------------------------------ #

    def _pull_github_alert_element(self, el) -> str | None:
        """Convert a .markdown-alert element back to GitHub Alert Markdown syntax.

        Output format::
            > [!TYPE]
            > 第一段正文
            >
            > 第二段正文（多段落時）

        - 類型從 markdown-alert-{type} class 提取，輸出全大寫
        - .markdown-alert-title 的 <p> 元素（含 SVG）完全移除
        - 未知類型 fallback 為普通 blockquote
        """
        classes = el.get('class', [])
        alert_type = None
        for cls in classes:
            if cls.startswith('markdown-alert-') and cls != 'markdown-alert':
                candidate = cls[len('markdown-alert-'):].upper()
                if candidate in _ALERT_TYPES:
                    alert_type = candidate
                    break

        # 移除 .markdown-alert-title 元素（含 SVG）
        title_el = el.select_one('.markdown-alert-title')
        if title_el:
            title_el.decompose()

        # 收集剩餘 <p> 元素的正文
        paragraphs = [p.get_text(strip=True) for p in el.find_all('p')]
        # 過濾空段落
        paragraphs = [p for p in paragraphs if p]

        if alert_type is None:
            # Fallback: 未知類型 → 普通 blockquote
            lines = []
            for p in paragraphs:
                lines.append(f'> {p}')
            return '\n'.join(lines) if lines else ''

        # 正常輸出
        lines = [f'> [!{alert_type}]']
        for i, para in enumerate(paragraphs):
            lines.append(f'> {para}')
            if i < len(paragraphs) - 1:
                lines.append('>')  # 段落間空白行
        return '\n'.join(lines)

    # ------------------------------------------------------------------ #
    #  Code block protection helpers                                        #
    # ------------------------------------------------------------------ #

    _placeholders: dict = {}

    def _protect_code_blocks(self, content: str) -> str:
        self._placeholders = {}
        def hide(m):
            key = f'CODEBLOCK_{len(self._placeholders)}_'
            self._placeholders[key] = m.group(0)
            return key
        content = re.sub(r'```.*?```', hide, content, flags=re.DOTALL)
        content = re.sub(r'`[^`]+`', hide, content)
        return content

    def _restore_code_blocks(self, content: str) -> str:
        for key, original in self._placeholders.items():
            content = content.replace(key, original)
        return content
