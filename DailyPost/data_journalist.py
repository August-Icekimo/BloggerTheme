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
        # Convert {{token: {param}|opt={opt}}} style to named regex groups
        regex_pattern = re.escape(pattern)
        # Replace escaped {param} placeholders with named capture groups
        # We need to be careful with the escaping here.
        # Original placeholder in pattern is {param}. re.escape makes it \{param\}.
        # We want to match \{(\w+)\} and turn it into (?P<\1>[^}|\\n]+?)
        regex_pattern = re.sub(r'\\\{(\w+)\\\}', r'(?P<\1>[^}|\\n]+?)', regex_pattern)
        
        try:
            # We use finditer to handle multiple occurrences but be careful with replacements
            # Actually, using sub with a callback might be safer for complex replacements
            def replacer(match):
                params   = match.groupdict()
                rendered = template
                
                # Check for nested content that needs recursive translation
                token_def = self._tokens.get(token_name, {})
                push_def  = token_def.get('push', {})
                params_def = push_def.get('params', {})
                
                for p_name, p_meta in params_def.items():
                    if isinstance(p_meta, dict) and p_meta.get('type') == 'nested_tokens':
                        if p_name in params:
                            params[p_name] = self._push_tokens(params[p_name])
                
                for k, v in params.items():
                    rendered = rendered.replace('{' + k + '}', v or '')
                return rendered.strip()

            content = re.sub(regex_pattern, replacer, content)
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

    # ------------------------------------------------------------------ #
    #  PULL: HTML → Markdown                                               #
    # ------------------------------------------------------------------ #

    def html_to_markdown(self, html: str) -> str:
        """Convert Blogger HTML back to Markdown with token restoration."""
        soup = BeautifulSoup(html, 'lxml')
        # Process tokens outside-in (containers before children)
        self._pull_tokens_recursive(soup)
        # Remaining HTML → Markdown via html2text
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links     = False
        h.body_width       = 0
        h.ignore_images    = False
        h.protect_links    = True
        # html2text might need some fine-tuning for specific Blogger structures
        return h.handle(str(soup))

    def _pull_tokens_recursive(self, soup: BeautifulSoup) -> None:
        """Walk tokens in outside_in order, replace matched elements with token strings."""
        for token_name, token_def in self._tokens.items():
            pull_def = token_def.get('pull', {})
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
                    el.replace_with(token_str)

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
                # After recursion, we need the string representation
                # HTML2Text will be applied to the final result, but here we just need the tokens
                val = "".join(str(s) for s in inner_soup.contents)
            
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
