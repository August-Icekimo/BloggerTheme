---
title: SMS Token Test
labels: [test, sms]
---

# SMS Token Test Page

## 1. Basic Bubbles
{{sms-left: 你好，這是左邊的泡泡}}
{{sms-right: 收到，這是右邊的泡泡}}

## 2. Bubbles with Parameters
{{sms-left: 你好 | name=小明 | time=10:30}}
{{sms-right: 嗨 | name=小美 | time=10:31}}

## 3. Markdown inside Bubbles
{{sms-left: 這是 **粗體** 和 *斜體*}}
{{sms-right: 這是 `inline code` 和 [連結](https://google.com)}}

## 4. SMS Thread
{{sms-thread-start}}
{{sms-left: 進入對話模式}}
{{sms-right: 好的}}
{{sms-left: 這是第三句 | time=10:35}}
{{sms-thread-end}}

## 5. SMS Fold
{{sms-fold-start: 點擊展開對話紀錄}}
{{sms-thread-start}}
{{sms-left: 摺疊內的對話 1}}
{{sms-right: 摺疊內的對話 2}}
{{sms-thread-end}}
{{sms-fold-end}}

## 6. Edge Cases
- Empty message (should warn and skip): {{sms-left: }}
- Special characters: {{sms-left: 3 < 5 & "Quotes"}}
- Missing end tag: {{sms-thread-start}} (should be implicitly closed at end of file)
- Token inside code block (should NOT be expanded):
  `{{sms-left: 這裡不應該被展開}}`

  ```markdown
  {{sms-right: 這裡也不應該被展開}}
  ```

## 7. Existing Tokens (Regression Check)
{{youtube: dQw4w9WgXcQ}}

```mermaid
graph TD
    A --> B
```
